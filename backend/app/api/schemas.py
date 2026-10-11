"""API request/response schemas (the OpenAPI surface the TS client is
generated from)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.agents.contracts import ListingModel, SearchBriefInput


class BriefCreateRequest(BaseModel):
    text: str | None = None  # natural-language mode
    brief: SearchBriefInput | None = None  # structured mode


class BriefResponse(BaseModel):
    id: str
    raw_text: str | None
    data: SearchBriefInput
    created_at: datetime


class RunCreateRequest(BaseModel):
    brief_id: str


class RunCreateResponse(BaseModel):
    run_id: str


class ResumeRequest(BaseModel):
    approve: bool = True
    max_listings: int | None = Field(None, ge=1, le=50)


class RunSummary(BaseModel):
    id: str
    brief_id: str
    status: str
    interrupt: dict[str, Any] | None
    cost_usd: float
    tokens_in: int
    tokens_out: int
    cache_hits: int
    cache_misses: int
    critic_rejections: int
    started_at: datetime
    finished_at: datetime | None
    error: str | None


class ListingWithResults(BaseModel):
    listing: ListingModel
    match_score: float | None = None
    match_explanation: str | None = None
    results: dict[str, Any] = Field(default_factory=dict)  # agent -> AgentResult dump


class RunDetail(RunSummary):
    report: dict[str, Any] | None
    listings: dict[str, ListingWithResults] = Field(default_factory=dict)
