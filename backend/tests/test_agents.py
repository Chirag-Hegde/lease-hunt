from httpx import AsyncClient

from app.agents.commute import commute_agent, place_score
from app.agents.contracts import Fee, ListingModel, Place, SearchBriefInput
from app.agents.price import price_agent, select_comps, total_monthly_cost
from app.agents.scout import dedupe_listings
from app.graph.context import create_run_context, release_run_context
from app.seed.listings import generate_listings
from app.seed.load import seed


def _listing(**overrides: object) -> ListingModel:
    base: dict[str, object] = {
        "id": "test0001",
        "source": "demo",
        "address": "100 Test St, Sunnyvale, CA",
        "city": "Sunnyvale",
        "lat": 37.3700,
        "lng": -122.0350,
        "rent": 3200,
        "beds": 2.0,
        "baths": 2.0,
        "sqft": 1000,
        "amenities": ["dog friendly"],
    }
    base.update(overrides)
    return ListingModel.model_validate(base)


def _brief() -> SearchBriefInput:
    return SearchBriefInput(
        budget_max=3800,
        beds=2,
        baths=2,
        important_places=[
            Place(
                label="Work",
                address="Santa Clara",
                lat=37.3541,
                lng=-121.9552,
                weight=1.0,
                modes=["drive", "transit"],
                tolerance_minutes=20,
            )
        ],
    )


def test_place_score_nonlinear_penalty() -> None:
    assert place_score(0, 20) == 100.0
    at_tolerance = place_score(20, 20)
    assert 74.0 < at_tolerance <= 75.0
    # Beyond tolerance decays faster than within it.
    drop_within = place_score(10, 20) - place_score(20, 20)
    drop_beyond = place_score(20, 20) - place_score(30, 20)
    assert drop_beyond > drop_within
    assert place_score(60, 20) < 10


def test_dedupe_catches_seeded_duplicate() -> None:
    listings = generate_listings()
    deduped, removed = dedupe_listings(listings)
    assert removed >= 1
    assert len(deduped) == len(listings) - removed


async def test_commute_agent_scores_and_caches(client: AsyncClient) -> None:
    ctx = create_run_context("test-run-1", "u1", "b1", _brief())
    try:
        result = await commute_agent(ctx, _listing())
        assert result.status == "ok"
        assert result.data is not None
        score = result.data
        assert 0 < score.overall_score <= 100
        assert score.per_place[0].best_mode in ("drive", "transit")
        drive = score.per_place[0].by_mode["drive"]
        assert drive.peak_minutes > drive.offpeak_minutes
        misses_after_first = ctx.cache_misses
        assert misses_after_first > 0

        # Second listing at the same geohash cell reuses the cache.
        result2 = await commute_agent(ctx, _listing(id="test0002"))
        assert result2.status == "ok"
        assert ctx.cache_hits > 0
        assert ctx.cache_misses == misses_after_first
    finally:
        release_run_context("test-run-1")


async def test_commute_agent_unavailable_without_coords(client: AsyncClient) -> None:
    ctx = create_run_context("test-run-2", "u1", "b1", _brief())
    try:
        result = await commute_agent(ctx, _listing(lat=None, lng=None))
        assert result.status == "unavailable"
        assert result.reason is not None
    finally:
        release_run_context("test-run-2")


def test_total_monthly_cost_breakdown() -> None:
    fees = [
        Fee(name="utilities (flat RUBS)", amount=110, period="monthly", mandatory=True),
        Fee(name="admin fee", amount=300, period="one_time", mandatory=True),
        Fee(name="parking", amount=100, period="monthly", mandatory=False),
    ]
    total, breakdown = total_monthly_cost(3000, fees)
    assert total == 3110  # rent + RUBS; one-time and optional fees excluded
    assert "estimated utilities" not in breakdown  # bundled via RUBS


def test_select_comps_filters() -> None:
    listing = _listing()
    candidates = [
        _listing(id="c1", rent=3100, lat=37.3705, lng=-122.0340),  # good comp
        _listing(id="c2", rent=2900, beds=1.0),  # wrong beds
        _listing(id="c3", rent=3300, lat=37.2, lng=-121.7),  # too far
        _listing(id="c4", rent=3000, sqft=400),  # sqft out of ±20%
    ]
    comps = select_comps(listing, candidates)
    assert [c.id for c in comps] == ["c1"]


async def test_price_agent_percentile(client: AsyncClient) -> None:
    await seed()
    ctx = create_run_context("test-run-3", "u1", "b1", _brief())
    try:
        # Use a real seeded listing so there are nearby comps.
        listings = [
            listing
            for listing in generate_listings()
            if listing.city == "Sunnyvale" and listing.beds == 2.0
        ]
        result = await price_agent(ctx, listings[0])
        assert result.status in ("ok", "unavailable")
        if result.status == "ok":
            assert result.data is not None
            analysis = result.data
            assert analysis.comp_count >= 3
            assert 0 <= analysis.percentile <= 100
            assert analysis.fair_range_low <= analysis.fair_range_high
            assert analysis.total_monthly_cost >= listings[0].rent
            assert len(result.evidence) >= 1
    finally:
        release_run_context("test-run-3")
