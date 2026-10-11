"""Embedding providers. Mock = deterministic hash-seeded vectors so clustering
and similarity behave consistently offline."""

import hashlib

import numpy as np

from app.config import get_settings

EMBEDDING_DIM = 1536


class MockEmbeddings:
    name = "mock"
    dim = EMBEDDING_DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            # Combine token-level hash vectors so similar texts (shared words)
            # get similar embeddings — enough signal for demo clustering.
            acc = np.zeros(self.dim, dtype=np.float64)
            tokens = text.lower().split()
            for token in tokens:
                seed = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8], "big")
                rng = np.random.default_rng(seed)
                acc += rng.standard_normal(self.dim)
            if not tokens:
                acc = np.random.default_rng(0).standard_normal(self.dim)
            norm = float(np.linalg.norm(acc))
            vectors.append((acc / norm).tolist() if norm > 0 else acc.tolist())
        return vectors


class OpenAIEmbeddings:
    name = "openai"
    dim = EMBEDDING_DIM

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]


def get_embedding_provider() -> MockEmbeddings | OpenAIEmbeddings:
    settings = get_settings()
    if not settings.demo_mode and settings.openai_api_key:
        return OpenAIEmbeddings(settings.openai_api_key)
    return MockEmbeddings()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a), np.asarray(b)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return float(np.dot(va, vb) / denom) if denom else 0.0
