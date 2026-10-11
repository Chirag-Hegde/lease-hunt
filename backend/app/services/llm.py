"""LLMService: model routing, structured calls, cost accounting, budget
enforcement, and llm_calls logging. Agents never talk to providers directly."""

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from app.config import get_settings
from app.db import models
from app.db.session import get_session_factory
from app.providers.llm.anthropic_provider import AnthropicProvider
from app.providers.llm.base import LLMProvider, TModel
from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.openai_provider import OpenAIProvider
from app.services.budget import BudgetTracker
from app.services.prompts import load_prompt

logger = logging.getLogger(__name__)


@dataclass
class UsageAccumulator:
    """Collects LLM usage within one agent invocation (set by run_agent)."""

    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    calls: int = field(default=0)


current_usage: ContextVar[UsageAccumulator | None] = ContextVar("current_usage", default=None)


@dataclass
class ModelSpec:
    model: str
    input_per_mtok: float
    output_per_mtok: float


@dataclass
class LLMCallResult[TModel: object]:
    data: TModel
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


@lru_cache
def _load_models_config() -> dict[str, Any]:
    settings = get_settings()
    with open(settings.models_config_path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f)
    return config


def resolve_model(provider_name: str, task: str) -> ModelSpec:
    config = _load_models_config()
    tier = config["routing"].get(task, "fast")
    spec = config["providers"][provider_name][tier]
    return ModelSpec(
        model=spec["model"],
        input_per_mtok=float(spec["input_per_mtok"]),
        output_per_mtok=float(spec["output_per_mtok"]),
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicProvider(settings.anthropic_api_key)
    if settings.llm_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key)
    if settings.llm_provider not in ("mock", "anthropic", "openai"):
        logger.warning("unknown LLM_PROVIDER %r, using mock", settings.llm_provider)
    return MockLLMProvider()


class LLMService:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        budget: BudgetTracker | None = None,
        run_id: str | None = None,
        lease_id: str | None = None,
    ) -> None:
        self.provider = provider or get_llm_provider()
        self.budget = budget
        self.run_id = run_id
        self.lease_id = lease_id

    async def call(
        self,
        *,
        agent: str,
        task: str,
        schema: type[TModel],
        context: dict[str, Any] | None = None,
        max_tokens: int = 4096,
        **prompt_vars: object,
    ) -> LLMCallResult[TModel]:
        prompt_def = load_prompt(task)
        rendered = prompt_def.render(**prompt_vars)
        spec = resolve_model(self.provider.name, task)

        data, usage = await self.provider.complete(
            model=spec.model,
            task=task,
            system=prompt_def.system,
            prompt=rendered,
            schema=schema,
            context=context,
            max_tokens=max_tokens,
        )
        cost = (
            usage.tokens_in * spec.input_per_mtok + usage.tokens_out * spec.output_per_mtok
        ) / 1_000_000

        accumulator = current_usage.get()
        if accumulator is not None:
            accumulator.tokens_in += usage.tokens_in
            accumulator.tokens_out += usage.tokens_out
            accumulator.cost_usd += cost
            accumulator.calls += 1

        await self._record(
            agent, task, spec.model, prompt_def.version, usage_cost=cost, usage=usage
        )
        if self.budget is not None:
            self.budget.add(usage.tokens_in, usage.tokens_out, cost)

        return LLMCallResult(
            data=data,
            model=spec.model,
            prompt_version=prompt_def.version,
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            cost_usd=cost,
            latency_ms=usage.latency_ms,
        )

    async def _record(
        self,
        agent: str,
        task: str,
        model: str,
        prompt_version: str,
        *,
        usage_cost: float,
        usage: Any,
    ) -> None:
        try:
            async with get_session_factory()() as session:
                session.add(
                    models.LLMCall(
                        run_id=self.run_id,
                        lease_id=self.lease_id,
                        agent=agent,
                        task=task,
                        model=model,
                        prompt_version=prompt_version,
                        tokens_in=usage.tokens_in,
                        tokens_out=usage.tokens_out,
                        cost_usd=usage_cost,
                        latency_ms=usage.latency_ms,
                    )
                )
                await session.commit()
        except Exception:  # pragma: no cover - telemetry must never break a run
            logger.exception("failed to record llm call")
