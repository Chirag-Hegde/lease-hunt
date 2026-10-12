"""Precompute one complete demo run so the landing-page demo is instant.
Fleshed out once the orchestrator exists (build phase 3)."""

import asyncio
import os

# The canned demo run must be deterministic and free: force mock providers
# for this process even when backend/.env carries real keys.
os.environ["LLM_PROVIDER"] = "mock"
os.environ["RENTCAST_API_KEY"] = ""


async def precompute() -> None:
    from app.seed.demo_run import run_demo

    try:
        await run_demo()
    except NotImplementedError as exc:
        print(f"skipping demo run precompute: {exc}")


if __name__ == "__main__":
    asyncio.run(precompute())
