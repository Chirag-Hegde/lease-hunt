"""Distance-based commute estimator with time-of-day multipliers.

Deterministic: the same origin/dest/mode/period always yields the same
estimate, so cached and re-run results agree.
"""

import hashlib
import math

from app.agents.contracts import CommuteMode
from app.providers.commute.base import RouteEstimate, TimePeriod
from app.services.geo import haversine_m

# Effective door-to-door speeds (km/h) before peak multipliers, and a route
# shape factor (roads are not straight lines).
_SPEEDS_KMH: dict[CommuteMode, float] = {"drive": 44.0, "transit": 26.0, "bike": 14.5, "walk": 4.8}
_ROUTE_FACTOR = 1.32
_PEAK_MULTIPLIER: dict[CommuteMode, float] = {
    "drive": 1.65,  # 101/237/280 at rush hour
    "transit": 1.15,
    "bike": 1.05,
    "walk": 1.0,
}
_FIXED_OVERHEAD_MIN: dict[CommuteMode, float] = {
    "drive": 5.0,  # park + walk
    "transit": 9.0,  # wait + access
    "bike": 3.0,
    "walk": 1.0,
}


def _jitter(origin: tuple[float, float], dest: tuple[float, float], mode: str) -> float:
    """±8% deterministic variation so estimates don't look synthetic."""
    key = f"{origin[0]:.4f},{origin[1]:.4f}|{dest[0]:.4f},{dest[1]:.4f}|{mode}"
    digest = hashlib.sha256(key.encode()).digest()
    return 0.92 + (digest[0] / 255) * 0.16


class MockCommuteProvider:
    name = "mock"

    async def estimate(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        mode: CommuteMode,
        period: TimePeriod,
    ) -> RouteEstimate:
        distance_km = haversine_m(*origin, *dest) / 1000 * _ROUTE_FACTOR
        base_minutes = distance_km / _SPEEDS_KMH[mode] * 60 + _FIXED_OVERHEAD_MIN[mode]
        multiplier = _PEAK_MULTIPLIER[mode] if period == "peak" else 1.0
        minutes = base_minutes * multiplier * _jitter(origin, dest, mode)

        transfers: int | None = None
        note: str | None = None
        if mode == "transit":
            transfers = 0 if distance_km < 4 else (1 if distance_km < 12 else 2)
            if transfers >= 2:
                note = "Multiple transfers; delays compound at rush hour."
        if mode == "drive" and period == "peak" and distance_km > 8:
            note = "Rush-hour congestion on this corridor is highly variable."
        return RouteEstimate(minutes=round(minutes, 1), transfers=transfers, reliability_note=note)

    async def isochrone(
        self, center: tuple[float, float], mode: CommuteMode, minutes: int
    ) -> dict[str, object]:
        """Irregular polygon approximating the reachable area (peak traffic)."""
        speed_kmh = _SPEEDS_KMH[mode] / _PEAK_MULTIPLIER[mode]
        usable_minutes = max(minutes - _FIXED_OVERHEAD_MIN[mode], 2.0)
        radius_km = speed_kmh * (usable_minutes / 60) / _ROUTE_FACTOR

        seed = int.from_bytes(
            hashlib.sha256(f"{center}|{mode}|{minutes}".encode()).digest()[:4], "big"
        )
        lat, lng = center
        points: list[list[float]] = []
        n = 36
        for i in range(n):
            bearing = 2 * math.pi * i / n
            # Bearing-dependent wobble (0.75–1.0 of max radius) → organic shape.
            wobble = 0.75 + 0.25 * abs(math.sin(bearing * 3 + seed % 7))
            r_km = radius_km * wobble
            dlat = (r_km / 110.574) * math.cos(bearing)
            dlng = (r_km / (111.320 * math.cos(math.radians(lat)))) * math.sin(bearing)
            points.append([round(lng + dlng, 5), round(lat + dlat, 5)])
        points.append(points[0])
        return {
            "type": "Feature",
            "properties": {"mode": mode, "minutes": minutes, "provider": self.name},
            "geometry": {"type": "Polygon", "coordinates": [points]},
        }
