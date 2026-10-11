"""Application settings, loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    demo_mode: bool = True

    # Database: SQLite file by default so the demo runs with zero services.
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR}/leaselens.sqlite3"

    # Cache / queue: in-memory fallbacks when unset.
    redis_url: str | None = None

    # LLM
    llm_provider: str = "mock"  # mock | anthropic | openai
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    models_config_path: Path = BACKEND_DIR / "config" / "models.yaml"

    # External providers (mocks used when unset)
    rentcast_api_key: str | None = None
    openrouteservice_api_key: str | None = None
    google_places_api_key: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None

    # Budgets & orchestration
    run_budget_usd: float = 0.50
    run_budget_tokens: int = 200_000
    fanout_concurrency: int = 5
    deep_analysis_interrupt_threshold: int = 8

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_hours: int = 24 * 14

    # Uploads
    upload_dir: Path = DATA_DIR / "uploads"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_lease_pages: int = 100
    lease_retention_days: int = 30

    # Telemetry
    langfuse_host: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
