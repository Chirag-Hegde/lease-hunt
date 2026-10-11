"""Mock listings provider: reads the 150 seeded demo listings from the DB."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import ListingModel, SearchBriefInput
from app.db import models
from app.services.mappers import listing_row_to_model


class MockListingsProvider:
    name = "mock"

    async def search(self, brief: SearchBriefInput, session: AsyncSession) -> list[ListingModel]:
        stmt = select(models.Listing).where(models.Listing.source == "demo")
        # Loose pre-filter: beds exact-or-above, rent within 120% of budget so
        # the Scout can still surface "slightly over, but negotiable" options.
        stmt = stmt.where(models.Listing.beds >= brief.beds)
        stmt = stmt.where(models.Listing.rent <= int(brief.budget_max * 1.2))
        if brief.budget_min:
            stmt = stmt.where(models.Listing.rent >= brief.budget_min)
        if brief.cities:
            stmt = stmt.where(models.Listing.city.in_(brief.cities))
        rows = (await session.execute(stmt)).scalars().all()
        return [listing_row_to_model(row) for row in rows]
