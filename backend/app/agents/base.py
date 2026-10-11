"""Shared agent execution wrapper: events, timeout, error envelope, budget."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.agents.contracts import AgentResult
from app.config import get_settings
from app.graph.context import RunContext
from app.services.budget import BudgetExceededError

logger = logging.getLogger(__name__)


async def run_agent[T: BaseModel](
    ctx: RunContext,
    agent: str,
    fn: Callable[[], Awaitable[AgentResult[T]]],
    listing_id: str | None = None,
    timeout_s: float | None = None,
) -> AgentResult[T]:
    """Run one agent invocation with start/finish events and a typed error
    envelope. Never raises (except cancellation): failures become
    AgentResult(status=error/unavailable)."""
    settings = get_settings()
    payload: dict[str, object] = {}
    if listing_id:
        payload["listing_id"] = listing_id
    await ctx.bus.publish(ctx.run_id, "agent_started", agent=agent, payload=payload)

    started = time.monotonic()
    try:
        if ctx.budget.exceeded:
            result = AgentResult[T](
                agent=agent,
                status="unavailable",
                reason="run budget exhausted before this agent started",
                confidence=0.0,
            )
        else:
            result = await asyncio.wait_for(
                fn(), timeout=timeout_s or settings.agent_timeout_seconds
            )
    except BudgetExceededError as exc:
        result = AgentResult[T](
            agent=agent, status="partial", reason=f"stopped: {exc}", confidence=0.0
        )
        await ctx.bus.publish(
            ctx.run_id, "budget_exceeded", agent=agent, payload={"detail": str(exc)}
        )
    except TimeoutError:
        result = AgentResult[T](
            agent=agent, status="error", reason="agent timed out", confidence=0.0
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("agent %s failed", agent)
        result = AgentResult[T](agent=agent, status="error", reason=str(exc)[:500], confidence=0.0)

    if result.latency_ms == 0:
        result.latency_ms = int((time.monotonic() - started) * 1000)

    finish_payload: dict[str, object] = {
        **payload,
        "status": result.status,
        "confidence": result.confidence,
        "cost_usd": round(result.cost_usd, 6),
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "latency_ms": result.latency_ms,
        "evidence_count": len(result.evidence),
    }
    if result.reason:
        finish_payload["reason"] = result.reason
    await ctx.bus.publish(ctx.run_id, "agent_finished", agent=agent, payload=finish_payload)
    return result
