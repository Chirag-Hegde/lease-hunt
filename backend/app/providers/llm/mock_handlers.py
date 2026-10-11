"""Mock LLM task handlers. Each computes a deterministic, realistic response
from the structured context an agent passes alongside its prompt.

More handlers are registered next to the agents that need them; this module
holds the shared/basic ones.
"""

import re
from typing import Any

from pydantic import BaseModel

from app.agents.contracts import Place, SearchBriefInput
from app.providers.llm.mock import register_mock

_KNOWN_CITIES = ["Sunnyvale", "Santa Clara", "Mountain View", "Cupertino", "San Jose"]

_THEME_KEYWORDS: dict[str, list[str]] = {
    "pests": ["roach", "cockroach", "mice", "mouse", "rat", "pest", "bed bug", "ants"],
    "noise": ["noise", "thin wall", "loud", "hear my neighbor", "train horn", "freeway", "bowling"],
    "maintenance": [
        "work order",
        "maintenance",
        "broken",
        "repair",
        "elevator",
        "dishwasher",
        "ac died",
    ],
    "management": [
        "management",
        "office",
        "lease renewal",
        "deposit",
        "corporate",
        "rude",
        "never answers",
        "cleaning fee",
        "increase",
    ],
    "safety": ["break-in", "break in", "stolen bike", "tailgated", "unsafe", "lighting", "safe"],
    "parking": ["parking", "tow", "garage spot", "assigned spot", "guest spot"],
    "package_theft": ["package", "amazon", "locker", "stolen package"],
    "water_heat": ["hot water", "radiator", "heating", "water was shut", "windows leak", "heat"],
}

_POSITIVE_WORDS = [
    "great",
    "lovely",
    "amazing",
    "best",
    "good",
    "responsive",
    "smooth",
    "recommend",
    "quiet",
]
_NEGATIVE_WORDS = [
    "broken",
    "stolen",
    "roach",
    "complain",
    "rude",
    "worst",
    "unbelievable",
    "never",
    "problem",
    "wild",
    "joke",
    "downhill",
    "theft",
    "unsafe",
]


@register_mock("brief_parse")
def parse_brief_from_text(context: dict[str, Any]) -> SearchBriefInput:
    """Parse natural-language housing requests like
    '2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly'."""
    text = str(context.get("text", ""))
    lower = text.lower()

    # Budget: "$3,800", "under 3800", "max 3.8k"
    budget_max = 3500
    money = re.search(r"\$?\s*(\d{1,2})[.,]?(\d{3})\b|\$(\d(?:\.\d)?)k", lower)
    if money:
        if money.group(3):
            budget_max = int(float(money.group(3)) * 1000)
        else:
            budget_max = int(money.group(1) + money.group(2))

    # Beds/baths: "2b2b", "2 bed", "2br", "studio"
    beds, baths = 1.0, 1.0
    bb = re.search(r"(\d)\s*b\s*(\d)\s*b|(\d)\s*(?:bed|br)", lower)
    if bb:
        if bb.group(1):
            beds, baths = float(bb.group(1)), float(bb.group(2))
        else:
            beds = float(bb.group(3))
    if "studio" in lower:
        beds = 0.0

    pets = []
    if "dog" in lower:
        pets.append("dog")
    if "cat" in lower:
        pets.append("cat")

    cities = [c for c in _KNOWN_CITIES if c.lower() in lower]

    # Commute hints: "20 min to Santa Clara"
    places: list[Place] = []
    for m in re.finditer(
        r"(\d{1,2})\s*min(?:ute)?s?\s+(?:to|from)\s+([a-z][a-z ]+?)(?:[,.]|$)", lower
    ):
        tolerance = int(m.group(1))
        dest = m.group(2).strip().title()
        places.append(
            Place(
                label=f"Work ({dest})",
                address=dest,
                weight=1.0,
                modes=["drive", "transit"],
                arrival_time="09:00",
                tolerance_minutes=tolerance,
            )
        )
    # "near Sunnyvale Caltrain"
    near = re.search(r"near\s+([a-z][a-z ]+?)(?:[,.]|$)", lower)
    if near:
        places.append(
            Place(
                label=near.group(1).strip().title(),
                address=near.group(1).strip().title(),
                weight=0.6,
                modes=["walk", "bike"],
                tolerance_minutes=15,
            )
        )

    must_haves = []
    nice_to_haves = []
    if "laundry" in lower or "in-unit" in lower:
        must_haves.append("in-unit laundry")
    if "parking" in lower or "garage" in lower:
        nice_to_haves.append("parking")
    if "pool" in lower:
        nice_to_haves.append("pool")
    if "gym" in lower:
        nice_to_haves.append("gym")

    return SearchBriefInput(
        budget_max=budget_max,
        beds=beds,
        baths=baths,
        pets=pets,
        cities=cities or ["Sunnyvale"],
        important_places=places,
        must_haves=must_haves,
        nice_to_haves=nice_to_haves,
        parking_required="parking required" in lower,
        in_unit_laundry_required="in-unit laundry" in lower and "must" in lower,
    )


@register_mock("review_theme_label")
def label_review_cluster(context: dict[str, Any]) -> BaseModel:
    """Keyword-vote theme labeling + lexicon/rating sentiment for a cluster."""
    from app.agents.review import ClusterLabel

    texts = [str(t).lower() for t in context.get("texts", [])]
    joined = " ".join(texts)

    votes = {
        theme: sum(joined.count(kw) for kw in keywords)
        for theme, keywords in _THEME_KEYWORDS.items()
    }
    theme = max(votes, key=lambda t: votes[t]) if any(votes.values()) else "management"

    ratings = [r for r in context.get("ratings", []) if isinstance(r, int | float)]
    positive = sum(joined.count(w) for w in _POSITIVE_WORDS)
    negative = sum(joined.count(w) for w in _NEGATIVE_WORDS)
    lexicon = (positive - negative) / max(positive + negative, 1)
    if ratings:
        rating_sentiment = (sum(ratings) / len(ratings) - 3.0) / 2.0
        sentiment = 0.6 * rating_sentiment + 0.4 * lexicon
    else:
        sentiment = lexicon
    return ClusterLabel(theme=theme, sentiment=round(max(-1.0, min(1.0, sentiment)), 2))


# Ordered: first match wins. Heading is checked before body text.
_CLAUSE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("security_deposit", ["security deposit"]),
    (
        "early_termination",
        ["early termination", "terminates this lease prior", "must vacate before"],
    ),
    ("auto_renewal", ["automatically renew", "renewal"]),
    ("rent_increase", ["rent adjustment", "increase the monthly rent", "rent shall remain fixed"]),
    ("late_fees", ["late charge", "late fee"]),
    ("landlord_entry", ["right of entry", "enter the premises"]),
    ("subletting", ["sublet", "assignment"]),
    ("guest_limits", ["guest", "occupancy and guests", "unauthorized occupant"]),
    ("pets", ["pet"]),
    ("renters_insurance", ["renter's insurance", "renters insurance"]),
    ("joint_several_liability", ["jointly and severally", "joint and several"]),
    ("liability_waiver", ["waiver of liability", "indemnif", "releases landlord"]),
    ("attorneys_fees", ["attorney"]),
    ("arbitration", ["arbitration", "dispute resolution", "trial by jury"]),
    ("mold_pest_disclosure", ["mold", "pest control service"]),
    ("moveout_charges", ["move-out", "upon vacating"]),
    ("as_is", ["as-is", '"as-is"', "condition of premises"]),
    ("nonrefundable_fees", ["non-refundable", "move-in fee", "administrative fee"]),
    ("maintenance_responsibility", ["maintenance", "repairs"]),
    ("utilities", ["utilit"]),
    ("parking", ["parking"]),
]


@register_mock("clause_classify")
def classify_clause(context: dict[str, Any]) -> BaseModel:
    from app.agents.lease import ClauseClassification

    heading = str(context.get("heading") or "").lower()
    text = str(context.get("text") or "").lower()
    for clause_type, keywords in _CLAUSE_KEYWORDS:
        if any(kw in heading for kw in keywords):
            return ClauseClassification(clause_type=clause_type)
    for clause_type, keywords in _CLAUSE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return ClauseClassification(clause_type=clause_type)
    return ClauseClassification(clause_type="other")


@register_mock("clause_risk")
def assess_clause_risk(context: dict[str, Any]) -> BaseModel:
    from app.agents.lease import ClauseRiskAssessment

    rule = context.get("rule")
    default = context.get("default")
    source = rule or default
    if isinstance(source, dict):
        return ClauseRiskAssessment(
            severity=source.get("severity", "info"),
            explanation=str(source.get("explanation", "Standard lease provision.")),
            why_it_matters=str(source.get("why_it_matters", "No specific risk detected.")),
            suggested_ask=source.get("suggested_ask"),
            confidence=0.9 if rule else 0.72,
        )
    return ClauseRiskAssessment(
        severity="info",
        explanation="General lease provision with no specific risk pattern.",
        why_it_matters="Nothing in this clause changed the overall risk picture.",
        suggested_ask=None,
        confidence=0.5,
    )


@register_mock("critic_judge")
def judge_claim_support(context: dict[str, Any]) -> BaseModel:
    """Overlap-based verdict: the claim's content words must appear across the
    evidence excerpts; 'recurring' claims need support in ≥2 excerpts."""
    from app.agents.critic import STOPWORDS, ClaimVerdict

    claim = str(context.get("claim", "")).lower()
    excerpts = [str(e).lower() for e in context.get("excerpts", []) if str(e).strip()]
    if not excerpts:
        return ClaimVerdict(action="rejected", reason="no evidence excerpts provided")

    # Theme synonyms so "pests complaints" matches "roaches" in evidence.
    expansions = {
        "pests": ["roach", "mice", "mouse", "pest", "rat"],
        "noise": ["noise", "loud", "thin wall", "hear"],
        "maintenance": ["maintenance", "repair", "broken", "work order", "elevator"],
        "management": ["management", "office", "deposit", "fee", "increase", "corporate", "rude"],
        "safety": ["break-in", "break in", "stolen", "gate", "unsafe", "lighting"],
        "parking": ["parking", "tow", "spot"],
        "package theft": ["package", "locker", "stolen"],
        "water heat": ["hot water", "radiator", "heating", "water"],
        "5-star": ["5 star", "five-star", "amazing", "best", "incredible", "flawless", "gift card"],
    }
    words = [w.strip(".,()!") for w in claim.split() if w.strip(".,()!") not in STOPWORDS]
    terms = set(words)
    for key, synonyms in expansions.items():
        if key in claim:
            terms.update(synonyms)

    supporting = sum(1 for excerpt in excerpts if any(t and t in excerpt for t in terms))
    needed = 2 if "recurring" in claim or "5-star" in claim else 1
    if supporting >= needed:
        return ClaimVerdict(action="approved", reason=f"{supporting} excerpt(s) support the claim")
    if supporting == 1:
        return ClaimVerdict(
            action="downgraded", reason="only one excerpt supports a 'recurring' claim"
        )
    return ClaimVerdict(action="rejected", reason="no excerpt mentions the claimed issue")
