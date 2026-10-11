"""Precompute one complete demo run so the landing-page demo is instant.
Fleshed out once the orchestrator exists (build phase 3)."""

import asyncio


async def precompute() -> None:
    from app.seed.demo_run import run_demo

    try:
        await run_demo()
    except NotImplementedError as exc:
        print(f"skipping demo run precompute: {exc}")


if __name__ == "__main__":
    asyncio.run(precompute())
