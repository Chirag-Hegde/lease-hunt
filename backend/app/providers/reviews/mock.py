"""Mock reviews provider: reads seeded review/post fixtures from the DB."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.providers.reviews.base import ReviewDoc


class MockReviewsProvider:
    name = "mock"

    async def fetch(
        self, building_key: str, building_name: str | None, session: AsyncSession
    ) -> list[ReviewDoc]:
        # Demo fixtures use short keys ("cedar-grove"); translate from the
        # building name when the slugified key doesn't match directly.
        from app.seed.buildings import BUILDINGS

        keys = {building_key}
        for building in BUILDINGS:
            if building_name and building.name.lower() == building_name.lower():
                keys.add(building.key)
        stmt = select(models.ReviewSource).where(models.ReviewSource.building_key.in_(keys))
        rows = (await session.execute(stmt)).scalars().all()
        return [
            ReviewDoc(
                source_type=row.source_type,
                external_id=row.external_id,
                url=row.url,
                author=row.author,
                rating=row.rating,
                text=row.text or "",
                posted_at=row.posted_at,
            )
            for row in rows
        ]
