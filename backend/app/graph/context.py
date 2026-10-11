"""Per-run context: budget, event bus, providers. Lives outside graph state
(not serializable / not checkpointed); recreated on resume."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.agents.contracts import ListingModel, SearchBriefInput
from app.config import get_settings
from app.db import models
from app.db.session import get_session_factory
from app.providers.commute.base import CommuteProvider
from app.providers.commute.factory import get_commute_provider
from app.providers.geocode.base import Geocoder
from app.providers.geocode.factory import get_geocoder
from app.providers.listings.base import ListingsProvider
from app.providers.listings.factory import get_listings_provider
from app.providers.reviews.base import ReviewsProvider
from app.providers.reviews.factory import get_reviews_providers
from app.services.budget import BudgetTracker
from app.services.events import EventBus, get_event_bus
from app.services.llm import LLMService
from app.services.mappers import listing_row_to_model


@dataclass
class RunContext:
    run_id: str
    user_id: str
    brief_id: str
    brief: SearchBriefInput
    budget: BudgetTracker
    bus: EventBus
    llm: LLMService
    listings: ListingsProvider
    commute: CommuteProvider
    geocoder: Geocoder
    reviews: list[ReviewsProvider]
    cache_hits: int = 0
    cache_misses: int = 0
    critic_rejections: int = 0
    _listing_cache: dict[str, ListingModel] = field(default_factory=dict)

    def cache_listings(self, listings: list[ListingModel]) -> None:
        for listing in listings:
            self._listing_cache[listing.id] = listing

    async def get_listing(self, listing_id: str) -> ListingModel | None:
        cached = self._listing_cache.get(listing_id)
        if cached is not None:
            return cached
        async with get_session_factory()() as session:
            row = (
                await session.execute(select(models.Listing).where(models.Listing.id == listing_id))
            ).scalar_one_or_none()
        if row is None:
            return None
        listing = listing_row_to_model(row)
        self._listing_cache[listing_id] = listing
        return listing

    async def persist_listing_results(
        self, listing_id: str, results: dict[str, dict[str, Any]]
    ) -> None:
        """Write per-listing AgentResult envelopes to their tables."""
        table_map = {
            "commute": models.CommuteResult,
            "review": models.ReviewInsight,
            "price": models.PriceAnalysisRow,
        }
        async with get_session_factory()() as session:
            for agent_name, payload in results.items():
                table = table_map.get(agent_name)
                if table is None:
                    continue
                session.add(table(run_id=self.run_id, listing_id=listing_id, data=payload))
            await session.commit()


_contexts: dict[str, RunContext] = {}


def create_run_context(
    run_id: str, user_id: str, brief_id: str, brief: SearchBriefInput
) -> RunContext:
    settings = get_settings()
    budget = BudgetTracker(
        budget_usd=settings.run_budget_usd, budget_tokens=settings.run_budget_tokens
    )
    ctx = RunContext(
        run_id=run_id,
        user_id=user_id,
        brief_id=brief_id,
        brief=brief,
        budget=budget,
        bus=get_event_bus(),
        llm=LLMService(budget=budget, run_id=run_id),
        listings=get_listings_provider(),
        commute=get_commute_provider(),
        geocoder=get_geocoder(),
        reviews=get_reviews_providers(),
    )
    _contexts[run_id] = ctx
    return ctx


def get_run_context(run_id: str) -> RunContext:
    return _contexts[run_id]


def has_run_context(run_id: str) -> bool:
    return run_id in _contexts


def release_run_context(run_id: str) -> None:
    _contexts.pop(run_id, None)
