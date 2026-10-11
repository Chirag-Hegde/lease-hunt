"""LeaseLens API entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import dispose_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.is_sqlite:
        await init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LeaseLens API",
        version="0.1.0",
        description="Multi-agent apartment & lease hunter.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.routes_briefs import router as briefs_router
    from app.api.routes_health import router as health_router
    from app.api.routes_listings import router as listings_router
    from app.api.routes_runs import router as runs_router

    app.include_router(health_router)
    app.include_router(briefs_router)
    app.include_router(runs_router)
    app.include_router(listings_router)
    return app


app = create_app()
