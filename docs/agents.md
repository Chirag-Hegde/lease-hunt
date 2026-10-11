# Agent specifications

All agents return `AgentResult[T]`: status, typed data, evidence, confidence,
and their own token/cost/latency accounting. Failures become typed
`unavailable`/`error` results with reasons — never invented data.

| Agent | Model tier | Input | Output | Key logic |
|---|---|---|---|---|
| **Scout** | fast (extraction only) | `SearchBriefInput` | `ScoutOutput` | provider search → cross-source dedupe (normalized address, <30m + rent/beds similarity) → deal-breaker hard filter → match scoring with explanations → relax-constraint suggestions |
| **Commute** | none (computed) | listing × places × modes | `CommuteScore` | peak/off-peak per mode, geohash-pair cache (24h), nonlinear over-tolerance penalty (`100−25(t/tol)²`, then `75e^(−1.4Δ/tol)`), isochrone bands for the primary place |
| **Review** | fast (theme labels) | building reviews/posts | `ReviewInsights` | embed → greedy cosine clustering → one label call per cluster (fixed 8-theme taxonomy) → recency trends (180d) → fake-burst detection (≥4 near-5★ in 14d) → management score + red flags, short excerpts with links only |
| **Price** | none (computed) | listing + candidates | `PriceAnalysis` | comps = same beds, ≤1.5mi, ≤60d, sqft ±20% → percentile, p25–p75 fair range, $/sqft, true monthly cost breakdown |
| **Lease** | fast classify + strong risk | PDF | `LeaseAnalysis` | layout-aware extraction (page+bbox) → clause segmentation → 21-type taxonomy → rule-pack grounding (CA, versioned YAML, official sources, `verified` flags) → citations to exact spans → risk 0–100 + questions checklist |
| **Negotiator** | strong | listing + verified results + lease findings | `NegotiationBundle` | evidence-linked leverage points (deterministic ids), asks (rent/fees/parking/redlines), 3 tones × 3 lengths; never sends — copy/mailto only |
| **Critic** | strong (judge) | all claims | `CriticReport` | numeric recomputation + evidence hygiene + strict judge rubric; rejected claims removed & logged; verified badges |
| **Ranker** | none | all scores | `RunReport` | `final = Σ(w·s)/Σ(w)` over available dimensions; formula shown in UI; client re-ranks instantly |

Prompts live in `backend/app/prompts/*.md` with version headers; every call
logs its prompt version. Untrusted content (reviews, listings, lease text,
user input) is delimited in prompts with explicit ignore-instructions rules.
