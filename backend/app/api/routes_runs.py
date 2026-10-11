from collections.abc import Sequence  # noqa: TC003 (used in cast string)
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.agents.contracts import SearchBriefInput
from app.api.deps import CurrentUser, DbSession
from app.api.schemas import (
    ListingWithResults,
    ResumeRequest,
    RunCreateRequest,
    RunCreateResponse,
    RunDetail,
    RunSummary,
)
from app.api.sse import run_event_stream
from app.db import models
from app.graph import runner
from app.graph.context import create_run_context
from app.services.mappers import listing_row_to_model

router = APIRouter(prefix="/api/runs", tags=["runs"])


async def _get_run(run_id: str, user: CurrentUser, session: DbSession) -> models.Run:
    run = (
        await session.execute(
            select(models.Run).where(models.Run.id == run_id, models.Run.user_id == user.id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(404, "run not found")
    return run


def _summary(run: models.Run) -> dict[str, Any]:
    return {
        "id": run.id,
        "brief_id": run.brief_id,
        "status": run.status,
        "interrupt": run.interrupt,
        "cost_usd": run.cost_usd,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "cache_hits": run.cache_hits,
        "cache_misses": run.cache_misses,
        "critic_rejections": run.critic_rejections,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error": run.error,
    }


@router.post("", response_model=RunCreateResponse)
async def create_run(
    body: RunCreateRequest, user: CurrentUser, session: DbSession
) -> RunCreateResponse:
    brief_row = (
        await session.execute(
            select(models.SearchBrief).where(
                models.SearchBrief.id == body.brief_id,
                models.SearchBrief.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if brief_row is None:
        raise HTTPException(404, "brief not found")

    run = models.Run(brief_id=brief_row.id, user_id=user.id, status="pending")
    session.add(run)
    await session.commit()

    brief = SearchBriefInput.model_validate(brief_row.data)
    create_run_context(run.id, user.id, brief_row.id, brief)
    await runner.launch_run(run.id)
    return RunCreateResponse(run_id=run.id)


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str, user: CurrentUser, session: DbSession) -> RunDetail:
    run = await _get_run(run_id, user, session)

    listings: dict[str, ListingWithResults] = {}
    # Scout matches (score + explanation) come from the latest scout event?
    # No — report.ranked has listing ids; match data lives in scout output,
    # which is inside the checkpoint. We rebuild from persisted rows instead.
    report = run.result or {}
    ranked_ids = [entry["listing_id"] for entry in report.get("ranked", [])]
    if ranked_ids:
        rows = (
            (await session.execute(select(models.Listing).where(models.Listing.id.in_(ranked_ids))))
            .scalars()
            .all()
        )
        for row in rows:
            listings[row.id] = ListingWithResults(listing=listing_row_to_model(row))

        result_tables: list[
            tuple[
                type[models.CommuteResult]
                | type[models.ReviewInsight]
                | type[models.PriceAnalysisRow],
                str,
            ]
        ] = [
            (models.CommuteResult, "commute"),
            (models.ReviewInsight, "review"),
            (models.PriceAnalysisRow, "price"),
        ]
        for table, agent_name in result_tables:
            result_rows = cast(
                "Sequence[models.CommuteResult | models.ReviewInsight | models.PriceAnalysisRow]",
                (
                    await session.execute(
                        select(table).where(
                            table.run_id == run_id, table.listing_id.in_(ranked_ids)
                        )
                    )
                )
                .scalars()
                .all(),
            )
            for result_row in result_rows:
                if result_row.listing_id in listings:
                    listings[result_row.listing_id].results[agent_name] = result_row.data

    return RunDetail(**_summary(run), report=run.result, listings=listings)


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str, user: CurrentUser, session: DbSession, after: int = 0
) -> StreamingResponse:
    await _get_run(run_id, user, session)
    return StreamingResponse(
        run_event_stream(run_id, after_seq=after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{run_id}/resume", response_model=RunSummary)
async def resume_run(
    run_id: str, body: ResumeRequest, user: CurrentUser, session: DbSession
) -> RunSummary:
    run = await _get_run(run_id, user, session)
    if run.status != "interrupted":
        raise HTTPException(409, f"run is {run.status}, not interrupted")
    await runner.resume_run(run_id, {"approve": body.approve, "max_listings": body.max_listings})
    await session.refresh(run)
    return RunSummary(**_summary(run))


@router.get("", response_model=list[RunSummary])
async def list_runs(user: CurrentUser, session: DbSession) -> list[RunSummary]:
    runs = (
        (
            await session.execute(
                select(models.Run)
                .where(models.Run.user_id == user.id)
                .order_by(models.Run.started_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [RunSummary(**_summary(run)) for run in runs]
