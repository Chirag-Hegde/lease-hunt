"""LLM provider abstraction. All agent LLM calls are structured: a prompt in,
a validated Pydantic model out, plus usage accounting."""

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class LLMUsage:
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LLMProvider(Protocol):
    name: str

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
        """Return a schema-validated result.

        `context` carries the structured inputs that produced `prompt`; real
        providers ignore it, the mock provider uses it to compute a
        deterministic, realistic response offline.
        """
        ...


class EmbeddingProvider(Protocol):
    name: str
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
