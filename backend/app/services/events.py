"""Run event bus: persists every event to run_events and fans out to live
SSE subscribers. In-memory pub/sub (demo, single process); the publish/
subscribe seam is where Redis pub/sub slots in for multi-process workers."""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.db import models
from app.db.session import get_session_factory
from app.services.redact import redact_payload

EventType = Literal[
    "run_started",
    "agent_started",
    "tool_called",
    "partial_result",
    "agent_finished",
    "critic_rejected",
    "interrupt_required",
    "run_resumed",
    "budget_exceeded",
    "run_finished",
    "run_failed",
]


class RunEventModel(BaseModel):
    run_id: str
    seq: int = 0
    type: EventType
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[RunEventModel | None]]] = defaultdict(list)
        self._seq: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def publish(
        self,
        run_id: str,
        type_: EventType,
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RunEventModel:
        async with self._lock:
            self._seq[run_id] += 1
            seq = self._seq[run_id]
        event = RunEventModel(
            run_id=run_id,
            seq=seq,
            type=type_,
            agent=agent,
            payload=redact_payload(payload or {}),
        )

        async with get_session_factory()() as session:
            session.add(
                models.RunEvent(
                    run_id=run_id,
                    seq=event.seq,
                    type=event.type,
                    agent=event.agent,
                    payload=event.payload,
                    created_at=event.created_at,
                )
            )
            await session.commit()

        for queue in list(self._subscribers.get(run_id, [])):
            queue.put_nowait(event)
        return event

    def subscribe(self, run_id: str) -> asyncio.Queue[RunEventModel | None]:
        queue: asyncio.Queue[RunEventModel | None] = asyncio.Queue()
        self._subscribers[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEventModel | None]) -> None:
        subscribers = self._subscribers.get(run_id, [])
        if queue in subscribers:
            subscribers.remove(queue)

    async def close_run(self, run_id: str) -> None:
        """Signal end-of-stream to all subscribers."""
        for queue in list(self._subscribers.get(run_id, [])):
            queue.put_nowait(None)


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    global _bus
    _bus = None
