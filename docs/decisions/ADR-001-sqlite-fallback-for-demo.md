# ADR-001: SQLite fallback for demo mode and tests

## Status

Accepted

## Context

The product requirement is `make demo` must give a working app with **zero API
keys** — and we extend that to zero external services, so a reviewer can clone
the repo and run it on a laptop without Docker, Postgres, or Redis.

Production still wants Postgres 16 + pgvector (embedding search, concurrent
writers, PostGIS-adjacent geo queries) and Redis (shared cache, rate limiting,
arq job queue).

## Decision

- The database layer targets **both** engines through SQLAlchemy 2.x:
  - `DATABASE_URL` unset → SQLite (aiosqlite) file at `backend/data/`.
  - `DATABASE_URL=postgresql+asyncpg://...` → Postgres (docker compose).
- Two portable column types hide the differences (`app/db/types.py`):
  - `PortableJSON`: JSONB on Postgres, JSON/TEXT on SQLite.
  - `EmbeddingVector`: pgvector `vector(1536)` on Postgres, JSON-encoded list
    on SQLite. Vector similarity on SQLite is computed in Python with numpy —
    fine for demo-scale data (hundreds of chunks), replaced by pgvector ANN in
    production.
- Redis is likewise optional: `app/services/cache.py` provides an in-memory
  TTL cache when `REDIS_URL` is unset; orchestration runs in-process asyncio
  tasks instead of arq when there is no queue.
- Alembic migrations are authored portably and run on both engines; demo mode
  additionally supports `create_all` at startup for convenience.

## Consequences

- `make demo` and the entire test suite run offline on a bare machine.
- Demo-scale vector search is O(n) in Python; acceptable (< 1k vectors).
- CI exercises SQLite; a compose-based smoke job can exercise Postgres.
- The seams (cache, queue, vector search) are interfaces, so swapping the
  production implementation does not touch agent code.
