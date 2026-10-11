"""Seed loader: `uv run python -m app.seed.load`.

Idempotent — clears previous demo rows, then loads 150 listings, review
fixtures, and generates the 6 demo lease PDFs.
"""

import asyncio

from sqlalchemy import delete, select

from app.db import models
from app.db.session import dispose_engine, get_session_factory, init_db
from app.seed.leases import generate_leases
from app.seed.listings import generate_listings
from app.seed.reviews import generate_reviews
from app.services.mappers import listing_model_to_row

DEMO_USER_EMAIL = "demo@leaselens.dev"


async def seed() -> None:
    await init_db()
    factory = get_session_factory()
    async with factory() as session:
        # Demo user
        user = (
            await session.execute(select(models.User).where(models.User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = models.User(email=DEMO_USER_EMAIL)
            session.add(user)

        # Clear previous demo data (order matters for FKs)
        demo_listing_ids = select(models.Listing.id).where(models.Listing.source == "demo")
        for table in (
            models.CommuteResult,
            models.ReviewInsight,
            models.PriceAnalysisRow,
            models.ListingSource,
        ):
            await session.execute(delete(table).where(table.listing_id.in_(demo_listing_ids)))
        await session.execute(
            delete(models.ReviewSource).where(models.ReviewSource.external_id.like("demo-%"))
        )
        await session.execute(delete(models.Listing).where(models.Listing.source == "demo"))

        listings = generate_listings()
        for listing in listings:
            session.add(listing_model_to_row(listing))

        reviews = generate_reviews()
        for fixture in reviews:
            session.add(
                models.ReviewSource(
                    building_key=fixture.building_key,
                    source_type=fixture.source_type,
                    external_id=fixture.external_id,
                    url=fixture.url,
                    author=fixture.author,
                    rating=fixture.rating,
                    text=fixture.text,
                    posted_at=fixture.posted_at,
                )
            )

        await session.commit()

    manifest = generate_leases()
    print(
        f"seeded {len(listings)} listings, {len(reviews)} reviews, "
        f"{len(manifest)} lease PDFs (user: {DEMO_USER_EMAIL})"
    )


def main() -> None:
    asyncio.run(_run())


async def _run() -> None:
    try:
        await seed()
    finally:
        await dispose_engine()


if __name__ == "__main__":
    main()
