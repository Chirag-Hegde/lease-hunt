from typing import Protocol


class Geocoder(Protocol):
    name: str

    async def geocode(self, address: str) -> tuple[float, float] | None:
        """Return (lat, lng) or None when the address can't be resolved."""
        ...
