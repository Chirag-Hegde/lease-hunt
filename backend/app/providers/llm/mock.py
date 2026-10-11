"""Deterministic mock LLM. Each task has a handler that computes a realistic,
schema-valid response from the structured `context` — so the whole app runs
offline, repeatably, with zero API keys.

Handlers are registered in app.providers.llm.mock_handlers.
"""

import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from app.providers.llm.base import LLMUsage, TModel

MockHandler = Callable[[dict[str, Any]], BaseModel]

_HANDLERS: dict[str, MockHandler] = {}


def register_mock(task: str) -> Callable[[MockHandler], MockHandler]:
    def decorator(fn: MockHandler) -> MockHandler:
        _HANDLERS[task] = fn
        return fn

    return decorator


class MockLLMProvider:
    name = "mock"

    async def complete(
        self,
        *,
        model: str,
        task: str,
        system: str,
        prompt: str,
        schema: type[TModel],
        context: dict[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> tuple[TModel, LLMUsage]:
        # Import handlers lazily so registration happens on first use.
        from app.providers.llm import mock_handlers  # noqa: F401

        handler = _HANDLERS.get(task)
        if handler is None:
            raise KeyError(f"no mock handler registered for task {task!r}")
        started = time.monotonic()
        await asyncio.sleep(0.02)  # make streaming progress visible in the UI
        raw = handler(context or {})
        result = schema.model_validate(raw.model_dump()) if not isinstance(raw, schema) else raw
        out_json = json.dumps(result.model_dump(mode="json"))
        latency_ms = max(int((time.monotonic() - started) * 1000), 1)
        usage = LLMUsage(
            tokens_in=max((len(system) + len(prompt)) // 4, 1),
            tokens_out=max(len(out_json) // 4, 1),
            latency_ms=latency_ms,
        )
        return result, usage
