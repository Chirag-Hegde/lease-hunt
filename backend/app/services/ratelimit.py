"""Per-client sliding-window rate limit middleware (in-memory; swap the store
for Redis in multi-process deployments)."""

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

WINDOW_SECONDS = 60.0
EXEMPT_PATHS = {"/api/health", "/docs", "/openapi.json"}


class SlidingWindowLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()
        if len(window) >= self.limit:
            return False, WINDOW_SECONDS - (now - window[0])
        window.append(now)
        return True, 0.0


def install_rate_limiter(app: FastAPI, limit_per_minute: int) -> None:
    limiter = SlidingWindowLimiter(limit_per_minute)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        client = auth[-24:] if auth else (request.client.host if request.client else "anon")
        allowed, retry_after = limiter.check(client)
        if not allowed:
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
        response: Response = await call_next(request)
        return response
