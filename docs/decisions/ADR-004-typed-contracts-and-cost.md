# ADR-004: Typed contracts everywhere & cost controls

## Status

Accepted

## Context

Multi-agent systems rot fastest at the seams: untyped dicts passed between
agents hide drift until production. And LLM fan-out across 20 listings × 3
agents can silently multiply cost.

## Decision

**Contracts.** Every agent returns `AgentResult[T]` (Pydantic, generic):
status (`ok | partial | unavailable | error` — reason required on failure),
typed `data`, an evidence list, calibrated confidence, and its own
token/cost/latency accounting. Domain payloads (`CommuteScore`,
`ReviewInsights`, `PriceAnalysis`, `LeaseFinding`, `NegotiationDraft`,
`CriticReport`) are validated on write *and* read; `LeveragePoint` won't even
construct without evidence ids. The OpenAPI schema generates the TypeScript
client, so the frontend shares the same types.

**Cost.** Four layers:

1. **Model routing** (`config/models.yaml`): cheap/fast model for extraction
   and classification; strong model only for lease risk reasoning,
   negotiation writing, and critic judging.
2. **Run budgets**: a per-run `BudgetTracker` (tokens + dollars) that every
   LLM call flows through; exceeding it turns remaining agents into typed
   `unavailable` results instead of failing the run.
3. **Caching**: commute estimates keyed by
   `(origin_geohash7, dest_geohash7, mode, time_bucket)` with 24h TTL;
   hit/miss rates surface in run stats.
4. **Accounting**: every call lands in `llm_calls` (model, prompt version,
   tokens, cost, latency, cache flag) — the source of truth for the trace
   viewer, run stats, and the eval suite's cost percentiles.

## Consequences

- `mypy --strict` passes across the backend; contract drift is a compile
  error, not a runtime surprise.
- Honest degradation: a dead provider yields a visible "unavailable — reason"
  card, never invented data.
- Prompt files are versioned on disk (`app/prompts/*.md`) and the version is
  logged per call, so regressions are attributable.
