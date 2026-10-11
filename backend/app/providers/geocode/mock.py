"""Mock geocoder: static landmark/city table + deterministic jitter."""

import hashlib

# South Bay anchors used by seeds and the demo brief.
LANDMARKS: dict[str, tuple[float, float]] = {
    "sunnyvale caltrain": (37.3783, -122.0306),
    "sunnyvale": (37.3688, -122.0363),
    "santa clara": (37.3541, -121.9552),
    "santa clara caltrain": (37.3532, -121.9363),
    "mountain view": (37.3861, -122.0839),
    "mountain view caltrain": (37.3945, -122.0763),
    "cupertino": (37.3230, -122.0322),
    "san jose": (37.3382, -121.8863),
    "san jose diridon": (37.3297, -121.9026),
    "work (santa clara)": (37.3541, -121.9552),
    "levi's stadium": (37.4033, -121.9694),
    "santana row": (37.3209, -121.9476),
    "kaiser santa clara": (37.3853, -121.9634),
}

_CITY_CENTERS = {
    "sunnyvale": (37.3688, -122.0363),
    "santa clara": (37.3541, -121.9552),
    "mountain view": (37.3861, -122.0839),
    "cupertino": (37.3230, -122.0322),
    "san jose": (37.3382, -121.8863),
}


class MockGeocoder:
    name = "mock"

    async def geocode(self, address: str) -> tuple[float, float] | None:
        key = address.lower().strip().rstrip(".,")
        if key in LANDMARKS:
            return LANDMARKS[key]
        # City match anywhere in the string → jitter deterministically around
        # that city's center so repeated runs are stable.
        for city, (clat, clng) in _CITY_CENTERS.items():
            if city in key:
                digest = hashlib.sha256(key.encode()).digest()
                dlat = (digest[0] / 255 - 0.5) * 0.02  # ± ~1.1 km
                dlng = (digest[1] / 255 - 0.5) * 0.02
                return (clat + dlat, clng + dlng)
        return None
