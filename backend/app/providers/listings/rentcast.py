"""RentCast API provider (official API, free tier ~50 req/mo).

Active whenever RENTCAST_API_KEY is configured (even in demo mode): live
US-wide listing search, up to 3 cities per brief. RentCast does not return
listing photos, so `photos` stays empty — the UI only ever shows photos the
listing source actually provides.
"""

import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import ListingModel, SearchBriefInput

_US_STATES = frozenset(
    [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "DC",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    ]
)
_CITY_STATE = re.compile(r"^(?P<city>.+?)[,\s]+(?P<state>[A-Za-z]{2})\.?$")

_MAX_CITIES_PER_SEARCH = 3  # each city is one API call against the free tier


def split_city_state(raw: str) -> tuple[str, str | None]:
    """'Austin, TX' / 'Austin TX' -> ('Austin', 'TX'); 'Sunnyvale' -> ('Sunnyvale', None)."""
    match = _CITY_STATE.match(raw.strip())
    if match and match.group("state").upper() in _US_STATES:
        return match.group("city").strip(" ,"), match.group("state").upper()
    return raw.strip(), None


class RentCastProvider:
    name = "rentcast"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, brief: SearchBriefInput, session: AsyncSession) -> list[ListingModel]:
        cities = brief.cities[:_MAX_CITIES_PER_SEARCH] or ["Sunnyvale, CA"]
        listings: list[ListingModel] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for raw_city in cities:
                city, state = split_city_state(raw_city)
                params: dict[str, str | int] = {
                    "city": city,
                    "bedrooms": int(brief.beds),
                    "status": "Active",
                    "limit": 50,
                }
                if state:
                    params["state"] = state
                resp = await client.get(
                    "https://api.rentcast.io/v1/listings/rental/long-term",
                    headers={"X-Api-Key": self._api_key},
                    params=params,
                )
                resp.raise_for_status()
                for item in resp.json():
                    rent = item.get("price")
                    if rent is None or (brief.budget_max and rent > brief.budget_max * 1.2):
                        continue
                    listings.append(
                        ListingModel(
                            source="rentcast",
                            url=None,
                            address=item.get("formattedAddress", ""),
                            city=item.get("city"),
                            lat=item.get("latitude"),
                            lng=item.get("longitude"),
                            rent=int(rent),
                            beds=float(item.get("bedrooms") or brief.beds),
                            baths=float(item.get("bathrooms") or 1),
                            sqft=item.get("squareFootage"),
                            available_date=item.get("listedDate", "")[:10] or None,
                        )
                    )
        return listings
