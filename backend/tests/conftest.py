import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure(config: pytest.Config) -> None:
    # Each test session gets its own SQLite DB and runs fully offline.
    tmp = Path(os.environ.get("PYTEST_TMPDIR", "/tmp")) / f"leasehunt-test-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ["DEMO_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "mock"
    # Hermetic: a developer's backend/.env (real keys) must not leak into
    # tests — empty strings override dotenv values and read as "no key".
    for key in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "RENTCAST_API_KEY",
        "OPENROUTESERVICE_API_KEY",
        "GOOGLE_PLACES_API_KEY",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
    ):
        os.environ[key] = ""
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp}/test.sqlite3"
    os.environ.pop("REDIS_URL", None)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.db.session import dispose_engine, init_db
    from app.main import app

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await dispose_engine()
