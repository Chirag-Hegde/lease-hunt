"""Typed contracts passed between agents. No untyped dicts cross agent
boundaries: every agent returns AgentResult[T] with evidence attached."""

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Evidence & result envelope
# ---------------------------------------------------------------------------

SourceType = Literal["listing", "review", "reddit", "lease_pdf", "api", "computed"]
AgentStatus = Literal["ok", "partial", "unavailable", "error"]


def short_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Evidence(BaseModel):
    id: str = Field(default_factory=short_id)
    source_type: SourceType
    source_url: str | None = None
    excerpt: str | None = None  # short; truncated to 200 chars
    page: int | None = None  # for lease PDFs
    bbox: tuple[float, float, float, float] | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)

    @field_validator("excerpt")
    @classmethod
    def _truncate_excerpt(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 200:
            return v[:197] + "..."
        return v


class AgentResult[T](BaseModel):
    agent: str
    status: AgentStatus
    data: T | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str | None = None  # required when status != ok
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0

    @model_validator(mode="after")
    def _reason_required_on_failure(self) -> "AgentResult[T]":
        if self.status != "ok" and not self.reason:
            raise ValueError(f"reason is required when status={self.status!r}")
        return self


# ---------------------------------------------------------------------------
# Search brief
# ---------------------------------------------------------------------------

CommuteMode = Literal["drive", "transit", "bike", "walk"]


class Place(BaseModel):
    label: str
    address: str
    lat: float | None = None
    lng: float | None = None
    weight: float = Field(1.0, ge=0.0, le=1.0)
    modes: list[CommuteMode] = Field(
        default_factory=lambda: list[CommuteMode](("drive", "transit"))
    )
    arrival_time: str | None = "09:00"  # HH:MM, local
    tolerance_minutes: int = 30  # beyond this, the penalty curve steepens

    @field_validator("modes")
    @classmethod
    def _default_modes_when_empty(cls, v: list[CommuteMode]) -> list[CommuteMode]:
        # LLM brief parsing sometimes emits []; an unreachable place is never
        # what the user meant.
        return v or ["drive", "transit"]


class SearchBriefInput(BaseModel):
    budget_min: int | None = None
    budget_max: int
    beds: float = 1
    baths: float = 1
    move_in_earliest: date | None = None
    move_in_latest: date | None = None
    lease_months: int | None = 12
    pets: list[str] = Field(default_factory=list)  # e.g. ["dog"]
    parking_required: bool = False
    in_unit_laundry_required: bool = False
    must_haves: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    deal_breakers: list[str] = Field(default_factory=list)
    cities: list[str] = Field(
        default_factory=list,
        description='US cities to search, each as "City" or "City, ST" when a state is known',
    )
    important_places: list[Place] = Field(default_factory=list)
    max_listings: int = 20


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


class Fee(BaseModel):
    name: str
    amount: float
    period: Literal["monthly", "one_time"] = "monthly"
    mandatory: bool = True


class ListingModel(BaseModel):
    id: str = Field(default_factory=short_id)
    source: str  # demo | rentcast | user_url | user_text
    url: str | None = None
    address: str
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    rent: int
    deposit: int | None = None
    fees: list[Fee] = Field(default_factory=list)
    beds: float
    baths: float
    sqft: int | None = None
    amenities: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    available_date: str | None = None
    landlord: str | None = None
    building_name: str | None = None
    raw_text: str | None = None
    listed_at: datetime | None = None


class ScoutMatch(BaseModel):
    listing: ListingModel
    match_score: float = Field(ge=0.0, le=100.0)
    matched_must_haves: list[str] = Field(default_factory=list)
    matched_nice_to_haves: list[str] = Field(default_factory=list)
    explanation: str


class ScoutOutput(BaseModel):
    matches: list[ScoutMatch]
    total_candidates: int
    deduped: int
    relax_suggestion: str | None = None  # set when few/no results


# ---------------------------------------------------------------------------
# Commute
# ---------------------------------------------------------------------------


class LegEstimate(BaseModel):
    peak_minutes: float
    offpeak_minutes: float
    transfers: int | None = None
    reliability_note: str | None = None


class PlaceCommute(BaseModel):
    place_label: str
    weight: float
    by_mode: dict[CommuteMode, LegEstimate]
    best_mode: CommuteMode
    best_peak_minutes: float


class CommuteScore(BaseModel):
    per_place: list[PlaceCommute]
    overall_score: float = Field(ge=0.0, le=100.0)
    formula: str  # human-readable explanation of the weighting


class IsochroneBand(BaseModel):
    minutes: int
    mode: CommuteMode
    geojson: dict[str, object]  # GeoJSON Feature (Polygon)


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

ReviewTheme = Literal[
    "pests",
    "noise",
    "maintenance",
    "management",
    "safety",
    "parking",
    "package_theft",
    "water_heat",
]

REVIEW_THEMES: tuple[ReviewTheme, ...] = (
    "pests",
    "noise",
    "maintenance",
    "management",
    "safety",
    "parking",
    "package_theft",
    "water_heat",
)


class ThemeInsight(BaseModel):
    theme: ReviewTheme
    frequency: int  # number of mentions
    sentiment: float = Field(ge=-1.0, le=1.0)  # -1 very negative .. +1 positive
    trend: Literal["improving", "stable", "worsening"]
    recent_spike: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewInsights(BaseModel):
    building_key: str
    review_count: int
    themes: list[ThemeInsight]
    management_score: float = Field(ge=0.0, le=100.0)
    red_flags: list[str] = Field(default_factory=list)
    fake_review_suspicion: bool = False
    fake_review_note: str | None = None


# ---------------------------------------------------------------------------
# Price / comps
# ---------------------------------------------------------------------------


class PriceAnalysis(BaseModel):
    comp_ids: list[str]
    comp_count: int
    median_ppsf: float | None = None
    listing_ppsf: float | None = None
    percentile: float = Field(ge=0.0, le=100.0)  # of rent vs comps (lower = cheaper)
    fair_range_low: int
    fair_range_high: int
    total_monthly_cost: float  # rent + mandatory fees + parking + est. utilities
    monthly_cost_breakdown: dict[str, float] = Field(default_factory=dict)
    method: str


# ---------------------------------------------------------------------------
# Lease analysis
# ---------------------------------------------------------------------------

ClauseType = Literal[
    "security_deposit",
    "nonrefundable_fees",
    "early_termination",
    "auto_renewal",
    "rent_increase",
    "late_fees",
    "maintenance_responsibility",
    "landlord_entry",
    "subletting",
    "guest_limits",
    "pets",
    "utilities",
    "parking",
    "renters_insurance",
    "joint_several_liability",
    "liability_waiver",
    "attorneys_fees",
    "arbitration",
    "mold_pest_disclosure",
    "moveout_charges",
    "as_is",
    "other",
]

Severity = Literal["info", "caution", "high"]


class LeaseCitation(BaseModel):
    page: int  # 1-indexed
    bbox: tuple[float, float, float, float]  # PDF points: x0, y0, x1, y1
    quote: str


class JurisdictionNote(BaseModel):
    rule_id: str
    text: str
    source_url: str | None = None
    verified: bool = False  # unverified rules are shown as "worth asking about"


class LeaseFindingModel(BaseModel):
    id: str = Field(default_factory=short_id)
    clause_type: ClauseType
    severity: Severity
    explanation: str  # plain English
    why_it_matters: str
    suggested_ask: str | None = None  # redline / question for the landlord
    citation: LeaseCitation
    jurisdiction_note: JurisdictionNote | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class LeaseAnalysis(BaseModel):
    lease_id: str
    risk_score: int = Field(ge=0, le=100)
    findings: list[LeaseFindingModel]
    page_count: int
    ocr_used: bool = False
    questions_for_landlord: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Not legal advice. Verify with a local tenant rights organization or attorney."
    )


# ---------------------------------------------------------------------------
# Negotiation
# ---------------------------------------------------------------------------

Tone = Literal["friendly", "firm", "data-driven"]


class LeveragePoint(BaseModel):
    id: str = Field(default_factory=short_id)
    text: str
    evidence_ids: list[str]  # must be non-empty: every point cites evidence
    kind: Literal["price", "reputation", "lease", "market", "timing"]

    @field_validator("evidence_ids")
    @classmethod
    def _non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("every leverage point must reference evidence")
        return v


class Ask(BaseModel):
    kind: Literal[
        "rent_reduction",
        "waived_fee",
        "free_parking",
        "lease_term",
        "move_in_date",
        "clause_redline",
    ]
    text: str


class NegotiationDraft(BaseModel):
    tone: Tone
    subject: str
    body: str
    leverage_points: list[LeveragePoint]
    asks: list[Ask]


class NegotiationBundle(BaseModel):
    listing_id: str
    drafts: list[NegotiationDraft]  # one per tone


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------


class ClaimReview(BaseModel):
    claim: str
    agent: str
    action: Literal["approved", "downgraded", "rejected"]
    reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class CriticReport(BaseModel):
    reviews: list[ClaimReview]
    approved: int
    downgraded: int
    rejected: int

    @model_validator(mode="after")
    def _counts_match(self) -> "CriticReport":
        counts = {"approved": 0, "downgraded": 0, "rejected": 0}
        for r in self.reviews:
            counts[r.action] += 1
        if (counts["approved"], counts["downgraded"], counts["rejected"]) != (
            self.approved,
            self.downgraded,
            self.rejected,
        ):
            raise ValueError("critic counts do not match reviews")
        return self


# ---------------------------------------------------------------------------
# Ranking & run report
# ---------------------------------------------------------------------------


class RankWeights(BaseModel):
    match: float = 0.2
    commute: float = 0.25
    value: float = 0.2
    reputation: float = 0.15
    lease_risk: float = 0.2


class DimensionScores(BaseModel):
    match: float | None = None
    commute: float | None = None
    value: float | None = None
    reputation: float | None = None
    lease_risk: float | None = None  # higher = safer (inverted risk)


class RankedListing(BaseModel):
    listing_id: str
    scores: DimensionScores
    final_score: float
    top_pros: list[str] = Field(default_factory=list)
    top_red_flag: str | None = None
    critic_verified: bool = False


class RunReport(BaseModel):
    run_id: str
    brief_id: str
    ranked: list[RankedListing]
    weights: RankWeights
    formula: str
    critic: CriticReport | None = None
    relax_suggestion: str | None = None
