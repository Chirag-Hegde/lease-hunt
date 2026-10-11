"""Anthropic provider using structured outputs (messages.parse)."""

import time
from typing import Any

from anthropic import AsyncAnthropic

from app.providers.llm.base import LLMUsage, TModel


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

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
        started = time.monotonic()
        response = await self._client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        parsed = response.parsed_output
        if parsed is None:
            raise ValueError(f"model returned no parseable output for task {task!r}")
        usage = LLMUsage(
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=latency_ms,
        )
        return parsed, usage
