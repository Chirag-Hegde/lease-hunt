# ADR-003: Why a Critic/Verifier agent

## Status

Accepted

## Context

Agents that summarize reviews or compute benchmarks can emit claims that
sound right but aren't supported — the classic failure mode of LLM pipelines.
Showing a renter "recurring pest complaints" that no review actually supports
is worse than showing nothing.

## Decision

A dedicated Critic pass runs after the specialists and before ranking:

1. **Deterministic lanes first**: numbers are recomputed (price breakdown
   must sum to the stated total; the commute score must be re-derivable from
   its per-place estimates), and evidence hygiene is enforced (every text
   claim needs at least one excerpt; review claims need source URLs).
2. **LLM-as-judge with a strict rubric** for the rest: approved / downgraded
   / rejected, with "recurring" claims requiring ≥2 supporting excerpts.
3. **Consequences, not just logging**: rejected red flags are *removed* from
   the user-facing payload, logged in `critic_reports`, streamed as
   `critic_rejected` events, and counted in run stats. Listings whose every
   claim passes earn the "Verified by Critic" badge.

## Consequences

- The eval suite injects 20 deliberately unsupported claims: the Critic
  catches 100% with zero false positives on 15 supported claims (demo mode).
- One more strong-model call per text claim — bounded because deterministic
  lanes handle the numeric claims for free.
- The badge gives the UI an honest trust signal with a paper trail.
