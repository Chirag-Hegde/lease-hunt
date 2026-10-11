"""RentCast API provider (official API, free tier ~50 req/mo).
Used only when RENTCAST_API_KEY is configured and DEMO_MODE=false."""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import ListingModel, SearchBriefInput


class RentCastProvider:
    name = "rentcast"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, brief: SearchBriefInput, session: AsyncSession) -> list[ListingModel]:
        city = brief.cities[0] if brief.cities else "Sunnyvale"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.rentcast.io/v1/listings/rental/long-term",
                headers={"X-Api-Key": self._api_key},
                params={
                    "city": city,
                    "state": "CA",
                    "bedrooms": int(brief.beds),
                    "status": "Active",
                    "limit": 50,
                },
            )
        resp.raise_for_status()
        listings: list[ListingModel] = []
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
