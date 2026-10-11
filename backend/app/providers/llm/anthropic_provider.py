"""Anthropic provider.

Primary path: structured outputs via `messages.parse` (schema-enforced).
Fallback: some of our larger Pydantic schemas (e.g. SearchBriefInput) exceed
the structured-outputs complexity limit — for those the API returns
400 "Schema is too complex", and we retry with a plain generation that embeds
the JSON Schema in the prompt, then validate the JSON ourselves. Validation
failures surface as errors (never silently truncated data).
"""

import json
import re
import time
from typing import Any

from anthropic import APITimeoutError, AsyncAnthropic, BadRequestError

from app.providers.llm.base import LLMUsage, TModel

# Schemas known (or learned) to exceed the structured-outputs complexity
# limit skip the doomed attempt: the API spends ~3 minutes before returning
# "Schema is too complex", so guessing wrong is expensive.
_schema_too_complex: set[str] = set()

# Measured: our failing schemas serialize to >2KB, the passing ones to <600B.
_SCHEMA_BYTES_LIMIT = 1500

_STRUCTURED_TIMEOUT_S = 90.0

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _schema_probably_too_complex(schema: type[TModel]) -> bool:
    if schema.__name__ in _schema_too_complex:
        return True
    return len(json.dumps(schema.model_json_schema(), separators=(",", ":"))) > _SCHEMA_BYTES_LIMIT


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
        if _schema_probably_too_complex(schema):
            parsed, usage = await self._complete_json_fallback(
                model=model,
                task=task,
                system=system,
                prompt=prompt,
                schema=schema,
                max_tokens=max_tokens,
            )
        else:
            try:
                parsed, usage = await self._complete_structured(
                    model=model,
                    task=task,
                    system=system,
                    prompt=prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
            except BadRequestError as exc:
                if "schema" not in str(exc).lower():
                    raise
                _schema_too_complex.add(schema.__name__)
                parsed, usage = await self._complete_json_fallback(
                    model=model,
                    task=task,
                    system=system,
                    prompt=prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
            except APITimeoutError:
                # Don't cache: timeouts can be transient; but do finish the job.
                parsed, usage = await self._complete_json_fallback(
                    model=model,
                    task=task,
                    system=system,
                    prompt=prompt,
                    schema=schema,
                    max_tokens=max_tokens,
                )
        usage.latency_ms = int((time.monotonic() - started) * 1000)
        return parsed, usage

    async def _complete_structured(
        self,
        *,
        model: str,
        task: str,
        system: str,
        prompt: str,
        schema: type[TModel],
        max_tokens: int,
    ) -> tuple[TModel, LLMUsage]:
        response = await self._client.with_options(timeout=_STRUCTURED_TIMEOUT_S).messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            raise ValueError(f"model declined task {task!r} (stop_reason=refusal)")
        parsed = response.parsed_output
        if parsed is None:
            raise ValueError(f"model returned no parseable output for task {task!r}")
        return parsed, LLMUsage(
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=0,
        )

    async def _complete_json_fallback(
        self,
        *,
        model: str,
        task: str,
        system: str,
        prompt: str,
        schema: type[TModel],
        max_tokens: int,
    ) -> tuple[TModel, LLMUsage]:
        schema_json = json.dumps(schema.model_json_schema(), separators=(",", ":"))
        wrapped_system = (
            f"{system}\n\n"
            "Respond with ONLY a single JSON object (no prose, no code fences) that "
            f"validates against this JSON Schema:\n{schema_json}"
        )
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=wrapped_system,
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise ValueError(f"model declined task {task!r} (stop_reason=refusal)")
        if response.stop_reason == "max_tokens":
            raise ValueError(f"output truncated at {max_tokens} tokens for task {task!r}")
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        fence = _JSON_FENCE.search(text)
        if fence:
            text = fence.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        parsed = schema.model_validate_json(text)
        return parsed, LLMUsage(
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            latency_ms=0,
        )
