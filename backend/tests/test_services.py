import pytest

from app.services.budget import BudgetExceededError, BudgetTracker
from app.services.cache import MemoryCache
from app.services.geo import geohash, haversine_m, normalize_address


def test_haversine_known_distance() -> None:
    # Sunnyvale Caltrain → Santa Clara Caltrain ≈ 8.6 km
    d = haversine_m(37.3783, -122.0306, 37.3532, -121.9363)
    assert 8000 < d < 9200


def test_geohash_precision_and_stability() -> None:
    h1 = geohash(37.3688, -122.0363, precision=7)
    h2 = geohash(37.3688, -122.0363, precision=7)
    assert h1 == h2
    assert len(h1) == 7
    # Nearby point shares a long prefix
    h3 = geohash(37.3690, -122.0365, precision=7)
    assert h1[:5] == h3[:5]


def test_normalize_address_dedupes_variants() -> None:
    a = normalize_address("1044 Cedar Grove Lane, Sunnyvale, CA")
    b = normalize_address("1044 cedar grove ln sunnyvale ca")
    assert a == b


def test_budget_tracker_raises_when_exceeded() -> None:
    tracker = BudgetTracker(budget_usd=0.01, budget_tokens=1000)
    tracker.add(100, 50, 0.005)
    assert not tracker.exceeded
    with pytest.raises(BudgetExceededError):
        tracker.add(100, 50, 0.02)
    assert tracker.exceeded


async def test_memory_cache_ttl_and_hit_counting() -> None:
    cache = MemoryCache()
    assert await cache.get("missing") is None
    await cache.set("k", {"v": 1}, ttl_seconds=60)
    assert await cache.get("k") == {"v": 1}
    assert cache.hits == 1
    assert cache.misses == 1
