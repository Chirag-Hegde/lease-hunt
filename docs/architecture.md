# Architecture

## System shape

```
web (Next.js 14, App Router)          backend (FastAPI)
┌──────────────────────────┐          ┌────────────────────────────────────┐
│ Mission Control  (SSE)   │◀─events──│ EventBus → run_events + live queues│
│ Results Explorer (map)   │──REST───▶│ routes_* (briefs/runs/listings/    │
│ Lease Analyzer (react-pdf│          │   leases/negotiations/compare/...) │
│ Negotiation Studio       │          │ LangGraph supervisor (runner)      │
│ Trace Viewer             │          │   scout → plan ⇢ Send fan-out      │
└──────────────────────────┘          │   → critic → ranker                │
                                      │ providers (real + mock behind      │
                                      │   interfaces): llm/listings/geo/   │
                                      │   commute/reviews/embeddings       │
                                      │ services: budget, cache, events,   │
                                      │   llm routing, pdf, auth, redact   │
                                      └────────────────────────────────────┘
          SQLite (demo) / Postgres16+pgvector (prod) · Redis optional
```

## A run, end to end

1. `POST /api/briefs` — structured form or natural language (`brief_parse`
   task, fast model). Important places get geocoded.
2. `POST /api/runs` — creates the Run row + `RunContext` (budget tracker,
   providers, event bus handle), launches the graph as a background task.
3. **Scout** searches providers, dedupes across sources (normalized address,
   <30m geodistance + rent/beds similarity), hard-filters deal-breakers,
   scores matches with explanations.
4. **Plan** interrupts if more than N listings qualify (“Deep-analyze all 11?
   est. cost $0.12”). `POST /api/runs/{id}/resume` continues with the chosen
   cap.
5. **Fan-out**: each selected listing runs Commute, Review, and Price agents
   concurrently (LangGraph `Send` across listings, `asyncio.gather` within).
   Results persist to their tables as `AgentResult` JSON.
6. **Critic** verifies all claims (deterministic recomputation + LLM judge),
   strips unsupported ones, assigns verified badges.
7. **Ranker** blends dimension scores with user-adjustable weights (the same
   formula ships to the client for instant re-ranking) and attaches isochrone
   bands for the map.
8. Every step streams typed events over SSE; the UI renders them as the live
   agent graph, listing badges, and run stats.

## Event flow

`EventBus.publish` assigns a per-run sequence, persists to `run_events`,
redacts PII, and fans out to subscriber queues. The SSE endpoint replays
history (`?after=seq`) then live-tails; EventSource reconnects dedupe by
sequence number. Terminal events close the stream.

## Offline-first demo

Every external dependency sits behind an interface with a deterministic mock
(seeded data, hash-jittered geocoding, speed-model commutes, keyword/template
LLM handlers). `DEMO_MODE=true` + no keys selects all mocks; adding keys and
flipping `LLM_PROVIDER` swaps in real providers without touching agent code.
See [ADR-001](decisions/ADR-001-sqlite-fallback-for-demo.md).

## Data model

17 tables (see `backend/app/db/models.py`): relational columns for querying
(rent, beds, geo, severity, status) + JSON payload columns holding validated
contracts. `lease_chunks.embedding` is pgvector `vector(1536)` on Postgres,
JSON on SQLite (similarity computed in NumPy at demo scale).
