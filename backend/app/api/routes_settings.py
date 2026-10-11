from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    demo_mode: bool
    llm_provider: str
    run_budget_usd: float
    run_budget_tokens: int
    fanout_concurrency: int
    lease_retention_days: int
    # key presence only — never the values
    keys: dict[str, bool]


class SettingsUpdate(BaseModel):
    llm_provider: Literal["mock", "anthropic", "openai"] | None = None
    run_budget_usd: float | None = Field(None, gt=0, le=50)
    run_budget_tokens: int | None = Field(None, gt=0, le=5_000_000)
    fanout_concurrency: int | None = Field(None, ge=1, le=20)


def _response() -> SettingsResponse:
    settings = get_settings()
    return SettingsResponse(
        demo_mode=settings.demo_mode,
        llm_provider=settings.llm_provider,
        run_budget_usd=settings.run_budget_usd,
        run_budget_tokens=settings.run_budget_tokens,
        fanout_concurrency=settings.fanout_concurrency,
        lease_retention_days=settings.lease_retention_days,
        keys={
            "anthropic": bool(settings.anthropic_api_key),
            "openai": bool(settings.openai_api_key),
            "rentcast": bool(settings.rentcast_api_key),
            "openrouteservice": bool(settings.openrouteservice_api_key),
            "google_places": bool(settings.google_places_api_key),
            "reddit": bool(settings.reddit_client_id and settings.reddit_client_secret),
        },
    )


@router.get("", response_model=SettingsResponse)
async def read_settings(user: CurrentUser) -> SettingsResponse:
    return _response()


@router.patch("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, user: CurrentUser) -> SettingsResponse:
    """Runtime-adjustable knobs (apply to new runs; process-local)."""
    settings = get_settings()
    if body.llm_provider is not None:
        if body.llm_provider == "anthropic" and not settings.anthropic_api_key:
            raise HTTPException(422, "ANTHROPIC_API_KEY is not configured")
        if body.llm_provider == "openai" and not settings.openai_api_key:
            raise HTTPException(422, "OPENAI_API_KEY is not configured")
        settings.llm_provider = body.llm_provider
        from app.services.llm import get_llm_provider

        get_llm_provider.cache_clear()
    if body.run_budget_usd is not None:
        settings.run_budget_usd = body.run_budget_usd
    if body.run_budget_tokens is not None:
        settings.run_budget_tokens = body.run_budget_tokens
    if body.fanout_concurrency is not None:
        settings.fanout_concurrency = body.fanout_concurrency
    return _response()
