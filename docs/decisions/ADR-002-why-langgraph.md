# ADR-002: Why LangGraph for orchestration

## Status

Accepted

## Context

The orchestrator needs: parallel fan-out per listing with a concurrency cap,
durable state so runs can pause on a human-in-the-loop question and resume
(possibly after a process restart), retries/timeouts around flaky agents, and
a topology we can render live in the UI.

Alternatives considered: hand-rolled asyncio supervisor (we'd rebuild
checkpointing and interrupts ourselves), Celery chains (no first-class state
graph or interrupts), Temporal (operationally heavy for this scale).

## Decision

LangGraph `StateGraph` with:

- **`Send` API** for per-listing fan-out (`plan → analyze_listing × N`),
  bounded by `max_concurrency` config (default 5). Inside each listing task,
  the specialist agents (commute/review/price) run concurrently via
  `asyncio.gather`.
- **`interrupt()` / `Command(resume=...)`** for the deep-analysis approval
  gate. The run row records `status=interrupted` + the question payload; the
  UI shows a modal; `/api/runs/{id}/resume` re-invokes the graph.
- **Checkpointing** via `AsyncSqliteSaver` (demo) / Postgres saver (prod),
  keyed by `thread_id = run_id`, so resume works across restarts.
- A **reducer** (`merge_listing_results`) merges parallel per-listing writes
  into one state key without clobbering.

Heavy, non-serializable things (providers, budget tracker, event bus) live in
a per-run `RunContext` registry outside graph state, recreated on resume.

## Consequences

- Interrupt/resume and replay came nearly for free; the graph definition is
  ~150 lines.
- Graph state must stay JSON-serializable — enforced by keeping Pydantic
  dumps (not instances) in state.
- The UI's agent graph mirrors the real topology, which makes the
  orchestration legible to reviewers.
