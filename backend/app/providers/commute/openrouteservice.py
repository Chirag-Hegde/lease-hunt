"""OpenRouteService provider: drive/bike/walk routing + isochrones (free tier).
Transit is not supported by ORS → typed 'unavailable' handled by the agent."""

import httpx

from app.agents.contracts import CommuteMode
from app.providers.commute.base import RouteEstimate, TimePeriod

_ORS_PROFILES: dict[str, str] = {
    "drive": "driving-car",
    "bike": "cycling-regular",
    "walk": "foot-walking",
}

# ORS has no live-traffic model; approximate peak conditions.
_PEAK_MULTIPLIER = {"drive": 1.55, "bike": 1.05, "walk": 1.0}


class ORSUnsupportedModeError(Exception):
    pass


class OpenRouteServiceProvider:
    name = "openrouteservice"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._base = "https://api.openrouteservice.org"

    async def estimate(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        mode: CommuteMode,
        period: TimePeriod,
    ) -> RouteEstimate:
        profile = _ORS_PROFILES.get(mode)
        if profile is None:
            raise ORSUnsupportedModeError(f"OpenRouteService does not support mode {mode!r}")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base}/v2/directions/{profile}",
                headers={"Authorization": self._api_key},
                json={
                    "coordinates": [[origin[1], origin[0]], [dest[1], dest[0]]],
                },
            )
        resp.raise_for_status()
        summary = resp.json()["routes"][0]["summary"]
        minutes = summary["duration"] / 60
        if period == "peak":
            minutes *= _PEAK_MULTIPLIER.get(mode, 1.0)
        return RouteEstimate(minutes=round(minutes, 1))

    async def isochrone(
        self, center: tuple[float, float], mode: CommuteMode, minutes: int
    ) -> dict[str, object]:
        profile = _ORS_PROFILES.get(mode)
        if profile is None:
            raise ORSUnsupportedModeError(f"OpenRouteService does not support mode {mode!r}")
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self._base}/v2/isochrones/{profile}",
                headers={"Authorization": self._api_key},
                json={"locations": [[center[1], center[0]]], "range": [minutes * 60]},
            )
        resp.raise_for_status()
        feature: dict[str, object] = resp.json()["features"][0]
        return feature
