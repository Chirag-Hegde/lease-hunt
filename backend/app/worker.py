"""arq worker for production deployments (REDIS_URL required).

Demo mode doesn't use this — runs execute as in-process asyncio tasks. In
multi-process deployments the API enqueues jobs here instead, keeping the
same runner/analyze functions."""

from typing import Any

from arq.connections import RedisSettings

from app.agents.lease import analyze_lease
from app.config import get_settings
from app.graph import runner


async def run_search(ctx: dict[str, Any], run_id: str) -> None:
    await runner.launch_run(run_id)
    await runner.wait_for_run(run_id)


async def resume_search(ctx: dict[str, Any], run_id: str, decision: dict[str, Any]) -> None:
    await runner.resume_run(run_id, decision)
    await runner.wait_for_run(run_id)


async def analyze_lease_job(ctx: dict[str, Any], lease_id: str) -> None:
    await analyze_lease(lease_id)


def _redis_settings() -> RedisSettings | None:
    url = get_settings().redis_url
    return RedisSettings.from_dsn(url) if url else None  # None → arq's localhost default


class WorkerSettings:
    functions = [run_search, resume_search, analyze_lease_job]
    redis_settings = _redis_settings()
    max_jobs = 4
