SHELL := /bin/bash
UV ?= uv
BACKEND := backend
WEB := web

.PHONY: setup setup-backend setup-web demo seed api worker web dev test test-backend test-web lint typecheck evals db-upgrade clean

## ---- Setup --------------------------------------------------------------

setup: setup-backend setup-web ## Install all dependencies

setup-backend:
	cd $(BACKEND) && $(UV) sync --all-extras

setup-web:
	cd $(WEB) && npm install

## ---- Demo (zero API keys, zero external services) -----------------------

demo: setup seed ## Seed demo data + precompute a run, then start api+web
	cd $(BACKEND) && $(UV) run python -m app.seed.precompute_demo_run
	@echo ""
	@echo "Demo ready. Starting API (:8000) and web (:3000)..."
	@$(MAKE) -j2 api web

seed:
	cd $(BACKEND) && $(UV) run python -m app.seed.load

## ---- Run ----------------------------------------------------------------

api:
	cd $(BACKEND) && DEMO_MODE=$${DEMO_MODE:-true} $(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000

worker:
	cd $(BACKEND) && $(UV) run arq app.worker.WorkerSettings

web:
	cd $(WEB) && npm run dev

dev: ## API + web with reload (expects `make seed` run once)
	@$(MAKE) -j2 api web

## ---- Quality ------------------------------------------------------------

test: test-backend test-web

test-backend:
	cd $(BACKEND) && $(UV) run pytest -q

test-web:
	cd $(WEB) && npm run test -- --run

test-e2e:
	cd $(WEB) && npx playwright test

lint:
	cd $(BACKEND) && $(UV) run ruff check app tests && $(UV) run ruff format --check app tests
	cd $(WEB) && npm run lint

typecheck:
	cd $(BACKEND) && $(UV) run mypy app
	cd $(WEB) && npm run typecheck

evals:
	cd $(BACKEND) && $(UV) run python -m evals.run --suite all

db-upgrade:
	cd $(BACKEND) && $(UV) run alembic upgrade head

clean:
	rm -rf $(BACKEND)/data $(BACKEND)/.venv $(WEB)/node_modules $(WEB)/.next
