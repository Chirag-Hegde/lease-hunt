from datetime import datetime
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class ReviewDoc(BaseModel):
    source_type: str  # google | reddit | demo
    external_id: str | None = None
    url: str | None = None
    author: str | None = None
    rating: float | None = None
    text: str
    posted_at: datetime | None = None


class ReviewsProvider(Protocol):
    name: str

    async def fetch(
        self, building_key: str, building_name: str | None, session: AsyncSession
    ) -> list[ReviewDoc]: ...
