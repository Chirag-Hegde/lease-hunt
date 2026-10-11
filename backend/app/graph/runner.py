"""Run lifecycle: launch, interrupt handling, resume, persistence of results.

Demo mode executes runs as in-process asyncio tasks; the arq worker calls the
same functions in production.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from sqlalchemy import select

from app.agents.contracts import SearchBriefInput
from app.config import DATA_DIR, get_settings
from app.db import models
from app.db.session import get_session_factory
from app.graph.build_graph import build_graph
from app.graph.context import (
    create_run_context,
    get_run_context,
    has_run_context,
    release_run_context,
)
from app.services.events import get_event_bus

logger = logging.getLogger(__name__)

CHECKPOINT_DB = DATA_DIR / "graph_checkpoints.sqlite3"

_tasks: dict[str, asyncio.Task[None]] = {}


async def _update_run(run_id: str, **fields: Any) -> None:
    async with get_session_factory()() as session:
        run = (
            await session.execute(select(models.Run).where(models.Run.id == run_id))
        ).scalar_one()
        for key, value in fields.items():
            setattr(run, key, value)
        await session.commit()


async def _ensure_context(run_id: str) -> None:
    if has_run_context(run_id):
        return
    async with get_session_factory()() as session:
        run = (
            await session.execute(select(models.Run).where(models.Run.id == run_id))
        ).scalar_one()
        brief_row = (
            await session.execute(
                select(models.SearchBrief).where(models.SearchBrief.id == run.brief_id)
            )
        ).scalar_one()
    brief = SearchBriefInput.model_validate(brief_row.data)
    create_run_context(run_id, run.user_id, run.brief_id, brief)


async def _execute(run_id: str, resume_value: Any | None = None) -> dict[str, Any]:
    settings = get_settings()
    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB)) as saver:
        graph = build_graph(saver)
        config: dict[str, Any] = {
            "configurable": {"thread_id": run_id},
            "max_concurrency": settings.fanout_concurrency,
        }
        graph_input: Any
        if resume_value is not None:
            graph_input = Command(resume=resume_value)
        else:
            graph_input = {"run_id": run_id, "listing_results": {}}
        state: dict[str, Any] = await graph.ainvoke(graph_input, config)
        return state


async def _drive(run_id: str, resume_value: Any | None = None) -> None:
    bus = get_event_bus()
    ctx = get_run_context(run_id)
    try:
        state = await _execute(run_id, resume_value)

        interrupts = state.get("__interrupt__")
        if interrupts:
            payload = interrupts[0].value if hasattr(interrupts[0], "value") else {}
            await _update_run(run_id, status="interrupted", interrupt=payload)
            await bus.publish(run_id, "interrupt_required", payload=payload)
            return  # keep context alive for resume

        report = state.get("report")
        await _update_run(
            run_id,
            status="finished",
            result=report,
            interrupt=None,
            cost_usd=ctx.budget.spent_usd,
            tokens_in=ctx.budget.tokens_in,
            tokens_out=ctx.budget.tokens_out,
            cache_hits=ctx.cache_hits,
            cache_misses=ctx.cache_misses,
            critic_rejections=ctx.critic_rejections,
            finished_at=datetime.now(UTC),
        )
        await bus.publish(
            run_id,
            "run_finished",
            payload={
                "cost_usd": round(ctx.budget.spent_usd, 6),
                "tokens": ctx.budget.total_tokens,
                "budget_exceeded": ctx.budget.exceeded,
                "listing_count": len((report or {}).get("ranked", [])),
            },
        )
        await bus.close_run(run_id)
        release_run_context(run_id)
    except Exception as exc:
        logger.exception("run %s failed", run_id)
        await _update_run(
            run_id, status="failed", error=str(exc)[:2000], finished_at=datetime.now(UTC)
        )
        await bus.publish(run_id, "run_failed", payload={"error": str(exc)[:500]})
        await bus.close_run(run_id)
        release_run_context(run_id)
    finally:
        _tasks.pop(run_id, None)


async def launch_run(run_id: str) -> None:
    """Start a run in the background (assumes Run row + context exist)."""
    await _ensure_context(run_id)
    await _update_run(run_id, status="running")
    await get_event_bus().publish(run_id, "run_started")
    _tasks[run_id] = asyncio.create_task(_drive(run_id))


async def resume_run(run_id: str, decision: dict[str, Any]) -> None:
    await _ensure_context(run_id)
    await _update_run(run_id, status="running", interrupt=None)
    _tasks[run_id] = asyncio.create_task(_drive(run_id, resume_value=decision))


async def wait_for_run(run_id: str) -> None:
    """Test/demo helper: wait until the background task completes."""
    task = _tasks.get(run_id)
    if task is not None:
        await task
