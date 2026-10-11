"""Mock LLM task handlers. Each computes a deterministic, realistic response
from the structured context an agent passes alongside its prompt.

More handlers are registered next to the agents that need them; this module
holds the shared/basic ones.
"""

import re
from typing import Any

from app.agents.contracts import Place, SearchBriefInput
from app.providers.llm.mock import register_mock

_KNOWN_CITIES = ["Sunnyvale", "Santa Clara", "Mountain View", "Cupertino", "San Jose"]


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
