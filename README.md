# LeaseLens

> Your apartment hunt, handled by a team of AI agents.

LeaseLens is a multi-agent system (LangGraph + FastAPI + Next.js) that scouts
listings, scores commutes, mines reviews for building red flags, analyzes
lease PDFs clause-by-clause with citations, benchmarks price against comps,
and drafts an evidence-backed negotiation email — with a Critic agent that
verifies every claim before it reaches you.

**Status: under construction, phase by phase.** See [docs/](docs/) and the
build phases in the project plan.

## Quickstart (zero API keys)

```bash
make demo   # installs deps, seeds demo data, starts api (:8000) + web (:3000)
```

Demo mode runs fully offline: mock LLM + data providers, SQLite, in-memory
cache. Set `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` in `backend/.env`
for real model calls.

## Development

```bash
make setup       # backend (uv) + web (npm)
make dev         # api + web with reload
make test        # pytest + vitest
make lint        # ruff + eslint
make typecheck   # mypy --strict + tsc
```

Docker: `docker compose up` brings up api, worker, web, Postgres 16 + pgvector,
Redis, and Langfuse.

## Not legal advice

Lease analysis is informational. Verify anything important with a local
tenant-rights organization or attorney.
