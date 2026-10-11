"""Google Places API (New) reviews provider.

Storage policy (per Google ToS): we persist the place_id and derived insights;
raw review text is kept only transiently for analysis and short excerpts with
attribution links.
"""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.reviews.base import ReviewDoc


class GooglePlacesProvider:
    name = "google_places"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def fetch(
        self, building_key: str, building_name: str | None, session: AsyncSession
    ) -> list[ReviewDoc]:
        query = building_name or building_key
        async with httpx.AsyncClient(timeout=15) as client:
            search = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName",
                },
                json={"textQuery": f"{query} apartments"},
            )
            search.raise_for_status()
            places = search.json().get("places", [])
            if not places:
                return []
            place_id = places[0]["id"]

            details = await client.get(
                f"https://places.googleapis.com/v1/places/{place_id}",
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": "reviews,googleMapsUri",
                },
            )
            details.raise_for_status()
            body = details.json()

        docs: list[ReviewDoc] = []
        for review in body.get("reviews", []):
            docs.append(
                ReviewDoc(
                    source_type="google",
                    external_id=place_id,
                    url=body.get("googleMapsUri"),
                    author=(review.get("authorAttribution") or {}).get("displayName"),
                    rating=review.get("rating"),
                    text=(review.get("text") or {}).get("text", ""),
                    posted_at=None,
                )
            )
        return docs
