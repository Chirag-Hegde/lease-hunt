from pathlib import Path

from sqlalchemy import func, select

from app.db import models
from app.db.session import get_session_factory
from app.seed.leases import generate_leases
from app.seed.listings import generate_listings
from app.seed.load import seed
from app.seed.reviews import generate_reviews


def test_listing_generator_shape() -> None:
    listings = generate_listings()
    assert len(listings) == 151  # 150 + 1 deliberate dupe
    cities = {listing.city for listing in listings}
    assert cities == {"Sunnyvale", "Santa Clara", "Mountain View", "Cupertino", "San Jose"}
    assert all(500 < listing.rent < 8000 for listing in listings)
    # Deterministic across calls
    again = generate_listings()
    assert [listing.rent for listing in again] == [listing.rent for listing in listings]


def test_review_fixtures_have_burst_and_spike() -> None:
    reviews = generate_reviews()
    assert len(reviews) >= 40
    aria = [r for r in reviews if r.building_key == "aria-station" and r.rating == 5.0]
    assert len(aria) >= 5  # the suspicious 5-star burst
    window_days = (max(r.posted_at for r in aria) - min(r.posted_at for r in aria)).days
    assert window_days <= 10


async def test_full_seed_loads_db_and_generates_leases(client: object, tmp_path: Path) -> None:
    await seed()
    async with get_session_factory()() as session:
        listing_count = (
            await session.execute(select(func.count()).select_from(models.Listing))
        ).scalar_one()
        review_count = (
            await session.execute(select(func.count()).select_from(models.ReviewSource))
        ).scalar_one()
    assert listing_count == 151
    assert review_count >= 40

    manifest = generate_leases(tmp_path)
    assert len(manifest) == 6
    kitchen_sink = next(m for m in manifest if m["key"] == "lease_6_el_camino_kitchen_sink")
    findings = kitchen_sink["expected_findings"]
    assert len(findings) >= 15
    assert all(f["page"] >= 1 and len(f["bbox"]) == 4 for f in findings)
    highs = [f for f in findings if f["severity"] == "high"]
    assert len(highs) >= 7
