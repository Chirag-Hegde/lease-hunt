"""Nominatim (OpenStreetMap) geocoder. Free; respect the 1 req/s usage policy."""

import asyncio

import httpx

_USER_AGENT = "Lease Hunt/0.1 (apartment search demo)"


class NominatimGeocoder:
    name = "nominatim"

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def geocode(self, address: str) -> tuple[float, float] | None:
        async with self._lock:  # serialize to respect rate policy
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": address, "format": "json", "limit": 1},
                    headers={"User-Agent": _USER_AGENT},
                )
            await asyncio.sleep(1.0)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        return (float(results[0]["lat"]), float(results[0]["lon"]))
