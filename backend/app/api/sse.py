"""Server-Sent Events stream of run events: replay persisted history, then
live-tail until the run reaches a terminal state."""

import asyncio
import json
from collections.abc import AsyncIterator

from sqlalchemy import select

from app.db import models
from app.db.session import get_session_factory
from app.services.events import RunEventModel, get_event_bus

TERMINAL_EVENTS = {"run_finished", "run_failed"}
KEEPALIVE_SECONDS = 15.0


def _format(event: RunEventModel) -> str:
    data = json.dumps(
        {
            "run_id": event.run_id,
            "seq": event.seq,
            "type": event.type,
            "agent": event.agent,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }
    )
    return f"id: {event.seq}\nevent: {event.type}\ndata: {data}\n\n"


async def run_event_stream(run_id: str, after_seq: int = 0) -> AsyncIterator[str]:
    bus = get_event_bus()
    queue = bus.subscribe(run_id)
    last_seq = after_seq
    try:
        # Replay history (subscribe-first avoids a gap; dedupe by seq).
        async with get_session_factory()() as session:
            rows = (
                (
                    await session.execute(
                        select(models.RunEvent)
                        .where(models.RunEvent.run_id == run_id, models.RunEvent.seq > after_seq)
                        .order_by(models.RunEvent.seq)
                    )
                )
                .scalars()
                .all()
            )
            run = (
                await session.execute(select(models.Run).where(models.Run.id == run_id))
            ).scalar_one_or_none()

        terminal_replayed = False
        for row in rows:
            event = RunEventModel(
                run_id=row.run_id,
                seq=row.seq,
                type=row.type,
                agent=row.agent,
                payload=row.payload,
                created_at=row.created_at,
            )
            last_seq = max(last_seq, row.seq)
            terminal_replayed = terminal_replayed or event.type in TERMINAL_EVENTS
            yield _format(event)

        if terminal_replayed or (
            run is not None and run.status in ("finished", "failed") and not rows
        ):
            return

        # Live tail.
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is None:
                return
            if item.seq <= last_seq:
                continue
            last_seq = item.seq
            yield _format(item)
            if item.type in TERMINAL_EVENTS:
                return
    finally:
        bus.unsubscribe(run_id, queue)
