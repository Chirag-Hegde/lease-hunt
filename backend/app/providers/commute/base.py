from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.contracts import CommuteMode

TimePeriod = Literal["peak", "offpeak"]


@dataclass
class RouteEstimate:
    minutes: float
    transfers: int | None = None
    reliability_note: str | None = None


class CommuteProvider(Protocol):
    name: str

    async def estimate(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        mode: CommuteMode,
        period: TimePeriod,
    ) -> RouteEstimate: ...

    async def isochrone(
        self, center: tuple[float, float], mode: CommuteMode, minutes: int
    ) -> dict[str, object]:
        """GeoJSON Feature (Polygon) reachable within `minutes`."""
        ...
