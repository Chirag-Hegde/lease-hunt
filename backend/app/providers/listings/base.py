from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import ListingModel, SearchBriefInput


class ListingsProvider(Protocol):
    name: str

    async def search(self, brief: SearchBriefInput, session: AsyncSession) -> list[ListingModel]:
        """Return candidate listings (loose filter; the Scout agent applies
        hard deal-breakers and scoring)."""
        ...
