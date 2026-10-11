"""Geo helpers: haversine distance, geohash, address normalization."""

import math
import re

EARTH_RADIUS_M = 6_371_000.0

_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

_ABBREVIATIONS = {
    "street": "st",
    "avenue": "ave",
    "boulevard": "blvd",
    "drive": "dr",
    "road": "rd",
    "lane": "ln",
    "court": "ct",
    "place": "pl",
    "terrace": "ter",
    "circle": "cir",
    "parkway": "pkwy",
    "expressway": "expy",
    "highway": "hwy",
    "apartment": "apt",
    "suite": "ste",
    "unit": "unit",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def geohash(lat: float, lng: float, precision: int = 7) -> str:
    """Standard geohash encoding (precision 7 ≈ 150m cell)."""
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    bits = 0
    bit_count = 0
    even = True
    result: list[str] = []
    while len(result) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            if lng >= mid:
                bits = (bits << 1) | 1
                lng_lo = mid
            else:
                bits <<= 1
                lng_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                bits = (bits << 1) | 1
                lat_lo = mid
            else:
                bits <<= 1
                lat_hi = mid
        even = not even
        bit_count += 1
        if bit_count == 5:
            result.append(_GEOHASH_BASE32[bits])
            bits = 0
            bit_count = 0
    return "".join(result)


def normalize_address(address: str) -> str:
    """Lowercase, strip punctuation, expand/contract common abbreviations —
    used for cross-source listing dedupe."""
    s = address.lower().strip()
    s = re.sub(r"[.,#]", " ", s)
    s = re.sub(r"\s+", " ", s)
    tokens = [(_ABBREVIATIONS.get(t, t)) for t in s.split(" ")]
    return " ".join(t for t in tokens if t)
