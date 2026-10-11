"""OpenAI provider using structured outputs (chat.completions.parse)."""

import time
from typing import Any

from openai import AsyncOpenAI

from app.providers.llm.base import LLMUsage, TModel


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)

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
        response = await self._client.chat.completions.parse(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            response_format=schema,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError(f"model returned no parseable output for task {task!r}")
        usage = response.usage
        return parsed, LLMUsage(
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )
