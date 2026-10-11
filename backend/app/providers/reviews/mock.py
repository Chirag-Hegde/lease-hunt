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
        stmt = select(models.ReviewSource).where(models.ReviewSource.building_key == building_key)
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
