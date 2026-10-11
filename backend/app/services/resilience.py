"""Retries + a minimal circuit breaker for external provider calls."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


class CircuitOpenError(Exception):
    pass


class CircuitBreaker:
    """Opens after `threshold` consecutive failures; half-opens after `cooldown_s`."""

    def __init__(self, name: str, threshold: int = 5, cooldown_s: float = 30.0) -> None:
        self.name = name
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._failures = 0
        self._opened_at: float | None = None

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at > self.cooldown_s:
            self._opened_at = None  # half-open: allow a probe
            self._failures = self.threshold - 1
            return False
        return True

    async def call(
        self,
        fn: Callable[[], Awaitable[T]],
        retries: int = 2,
        base_delay_s: float = 0.5,
    ) -> T:
        if self._is_open():
            raise CircuitOpenError(f"circuit for {self.name} is open")
        attempt = 0
        while True:
            try:
                result = await fn()
            except (TimeoutError, httpx.HTTPError) as exc:
                self._failures += 1
                if self._failures >= self.threshold:
                    self._opened_at = time.monotonic()
                if attempt >= retries:
                    raise
                await asyncio.sleep(base_delay_s * (2**attempt))
                attempt += 1
                if self._is_open():
                    raise CircuitOpenError(f"circuit for {self.name} is open") from exc
            else:
                self._failures = 0
                return result


_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]
