"""Tracing: every LLM call becomes an OpenTelemetry span (with token, cost,
and latency attributes) and, when configured, a Langfuse generation. All
no-ops unless configured; prompt/response text is never exported."""

import logging
from functools import lru_cache
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _tracer() -> trace.Tracer:
    provider = TracerProvider(resource=Resource.create({"service.name": "leasehunt-api"}))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("leasehunt")


@lru_cache
def _langfuse() -> Any | None:
    settings = get_settings()
    if not (
        settings.langfuse_host and settings.langfuse_public_key and settings.langfuse_secret_key
    ):
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )
    except Exception:  # pragma: no cover - optional dependency
        logger.warning("langfuse configured but client failed to initialize")
        return None


def record_llm_span(
    *,
    agent: str,
    task: str,
    model: str,
    prompt_version: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    latency_ms: int,
    run_id: str | None,
) -> None:
    with _tracer().start_as_current_span(f"llm.{task}") as span:
        span.set_attribute("llm.agent", agent)
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.prompt_version", prompt_version)
        span.set_attribute("llm.tokens_in", tokens_in)
        span.set_attribute("llm.tokens_out", tokens_out)
        span.set_attribute("llm.cost_usd", cost_usd)
        span.set_attribute("llm.latency_ms", latency_ms)
        if run_id:
            span.set_attribute("run.id", run_id)

    client = _langfuse()
    if client is not None:  # pragma: no cover - needs a live langfuse
        try:
            client.generation(
                name=f"{agent}/{task}",
                model=model,
                usage={"input": tokens_in, "output": tokens_out},
                metadata={
                    "run_id": run_id,
                    "prompt_version": prompt_version,
                    "cost_usd": cost_usd,
                    "latency_ms": latency_ms,
                },
            )
        except Exception:
            logger.debug("langfuse generation export failed", exc_info=True)
