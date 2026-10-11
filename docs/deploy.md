# Deploying

## Frontend — Vercel

1. Import the repo, set the project root to `web/`.
2. Env: `NEXT_PUBLIC_API_URL=https://<your-api-host>`.
3. Build command `npm run build` (the pdf.js worker is copied by `prebuild`).

## Backend — Fly.io

```bash
cd backend
fly launch --no-deploy            # generates fly.toml from the Dockerfile
fly postgres create               # or attach any Postgres 16 with pgvector
fly secrets set \
  DATABASE_URL=postgresql+asyncpg://... \
  REDIS_URL=redis://... \
  DEMO_MODE=false LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... \
  JWT_SECRET=$(openssl rand -hex 32)
fly deploy
fly ssh console -C "alembic upgrade head"
```

Run the worker as a second process group (`arq app.worker.WorkerSettings`) or
keep in-process execution (default) for small deployments.

## Backend — Render

- New Web Service from `backend/Dockerfile`; add a Render Postgres (enable
  the `vector` extension) and Key Value (Redis) instance; set the same env
  vars; add a one-off job for `alembic upgrade head`.

## Production checklist

- `DEMO_MODE=false`, real `JWT_SECRET`, HTTPS-only CORS origins
  (`CORS_ORIGINS='["https://your-app.vercel.app"]'`).
- Wire a mailer into `POST /api/auth/magic-link` (it intentionally returns
  501 in non-demo mode until you do).
- Optional: point `LANGFUSE_*` at the compose-hosted Langfuse for tracing.
- Postgres: migrations via Alembic; pgvector index on `lease_chunks.embedding`
  when corpus size warrants it.
