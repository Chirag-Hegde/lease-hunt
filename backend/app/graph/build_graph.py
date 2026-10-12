"""Supervisor graph:

scout → plan (human-in-the-loop interrupt) → fan-out per listing (Send) →
critic → rank → END

Per-listing specialist agents register in PER_LISTING_AGENTS; they run
concurrently per listing, and listings fan out in parallel with a
max_concurrency cap.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from app.agents.base import run_agent
from app.agents.contracts import AgentResult, ListingModel, RankWeights, ScoutOutput
from app.agents.ranker import FORMULA, rank_listings
from app.agents.scout import scout_agent
from app.config import get_settings
from app.graph.context import RunContext, get_run_context
from app.graph.state import ListingTask, RunState

# agent name -> factory(ctx, listing) -> AgentResult coroutine.
# Phases 4–5 register commute, price, and review agents here.
PerListingAgent = Callable[[RunContext, ListingModel], Awaitable[AgentResult[Any]]]
PER_LISTING_AGENTS: dict[str, PerListingAgent] = {}


def register_per_listing_agent(name: str, fn: PerListingAgent) -> None:
    PER_LISTING_AGENTS[name] = fn


def _scout_output(state: RunState) -> ScoutOutput | None:
    envelope = state.get("scout")
    if not envelope or envelope.get("data") is None:
        return None
    return ScoutOutput.model_validate(envelope["data"])


def _listing_by_id(state: RunState, listing_id: str) -> ListingModel | None:
    output = _scout_output(state)
    if output is None:
        return None
    for match in output.matches:
        if match.listing.id == listing_id:
            return match.listing
    return None


async def scout_node(state: RunState) -> dict[str, Any]:
    ctx = get_run_context(state["run_id"])

    async def _call() -> AgentResult[ScoutOutput]:
        return await scout_agent(ctx)

    result = await run_agent(ctx, "scout", _call)
    if result.data is not None:
        ctx.cache_listings([m.listing for m in result.data.matches])
    return {"scout": result.model_dump(mode="json")}


async def plan_node(state: RunState) -> dict[str, Any]:
    ctx = get_run_context(state["run_id"])
    settings = get_settings()
    output = _scout_output(state)
    if output is None or not output.matches:
        return {"selected_listing_ids": []}

    ids = [m.listing.id for m in output.matches]
    threshold = settings.deep_analysis_interrupt_threshold
    if len(ids) > threshold and PER_LISTING_AGENTS:
        est_cost = round(0.004 * len(PER_LISTING_AGENTS) * len(ids), 3)
        decision = interrupt(
            {
                "kind": "deep_analysis",
                "question": (
                    f"Scout found {len(ids)} matches. Deep-analyze all of them "
                    f"(commute, reviews, pricing), or just the top {threshold}?"
                ),
                "listing_count": len(ids),
                "default_top_n": threshold,
                "estimated_cost_usd": est_cost,
            }
        )
        if isinstance(decision, dict):
            if not decision.get("approve", True):
                ids = ids[:threshold]
            else:
                max_listings = decision.get("max_listings")
                if isinstance(max_listings, int) and max_listings > 0:
                    ids = ids[:max_listings]
        await ctx.bus.publish(ctx.run_id, "run_resumed", payload={"selected": len(ids)})
    return {"selected_listing_ids": ids}


def fan_out(state: RunState) -> list[Send] | str:
    ids = state.get("selected_listing_ids") or []
    if not ids or not PER_LISTING_AGENTS:
        return "critic"
    return [
        Send("analyze_listing", ListingTask(run_id=state["run_id"], listing_id=listing_id))
        for listing_id in ids
    ]


async def analyze_listing_node(task: ListingTask) -> dict[str, Any]:
    """Runs all registered specialist agents concurrently for one listing."""
    ctx = get_run_context(task["run_id"])
    listing_id = task["listing_id"]

    # Send nodes receive only their task payload; resolve the listing through
    # the context cache (falls back to the DB after a resume).
    listing = await ctx.get_listing(listing_id)
    if listing is None:
        return {"listing_results": {listing_id: {}}}

    names = list(PER_LISTING_AGENTS)

    def make_call(agent_name: str) -> Callable[[], Awaitable[AgentResult[Any]]]:
        def call() -> Awaitable[AgentResult[Any]]:
            return PER_LISTING_AGENTS[agent_name](ctx, listing)

        return call

    results = await asyncio.gather(
        *(run_agent(ctx, name, make_call(name), listing_id=listing_id) for name in names)
    )
    dumped: dict[str, Any] = {
        name: result.model_dump(mode="json") for name, result in zip(names, results, strict=True)
    }
    await ctx.persist_listing_results(listing_id, dumped)
    return {"listing_results": {listing_id: dumped}}


async def critic_node(state: RunState) -> dict[str, Any]:
    from app.agents.contracts import CriticReport
    from app.agents.critic import critic_agent
    from app.db import models
    from app.db.session import get_session_factory

    ctx = get_run_context(state["run_id"])
    listing_results = state.get("listing_results") or {}
    if not listing_results:
        return {"critic": None}

    outcome: dict[str, Any] = {}

    async def _call() -> AgentResult[CriticReport]:
        nonlocal outcome
        outcome = await critic_agent(ctx, listing_results)
        report = CriticReport.model_validate(outcome["report"])
        return AgentResult[CriticReport](
            agent="critic",
            status="ok",
            data=report,
            confidence=0.9,
            reason=None,
        )

    result = await run_agent(ctx, "critic", _call)
    if result.status != "ok" or result.data is None:
        return {"critic": None}

    async with get_session_factory()() as session:
        session.add(models.CriticReportRow(run_id=ctx.run_id, data=outcome["report"]))
        await session.commit()

    update: dict[str, Any] = {
        "critic": {
            "report": outcome["report"],
            "verified_listing_ids": outcome["verified_listing_ids"],
        }
    }
    if outcome["patched_results"]:
        update["listing_results"] = outcome["patched_results"]
        for listing_id, patched in outcome["patched_results"].items():
            await ctx.persist_listing_results(listing_id, patched)
    return update


async def _isochrone_bands(ctx: RunContext) -> list[dict[str, Any]]:
    """Isochrone for the primary (highest-weight) place so the UI can shade
    'reachable within tolerance' areas."""
    places = [p for p in ctx.brief.important_places if p.lat is not None and p.lng is not None]
    if not places:
        return []
    primary = max(places, key=lambda p: p.weight)
    mode = primary.modes[0] if primary.modes else "drive"
    bands: list[dict[str, Any]] = []
    for minutes in (primary.tolerance_minutes, int(primary.tolerance_minutes * 1.5)):
        try:
            assert primary.lat is not None and primary.lng is not None
            feature = await ctx.commute.isochrone((primary.lat, primary.lng), mode, minutes)
        except Exception:
            continue
        bands.append(
            {"place_label": primary.label, "mode": mode, "minutes": minutes, "geojson": feature}
        )
    return bands


async def rank_node(state: RunState) -> dict[str, Any]:
    ctx = get_run_context(state["run_id"])
    output = _scout_output(state)
    weights = RankWeights()
    critic = state.get("critic")
    verified: set[str] = set()
    if critic:
        verified = set(critic.get("verified_listing_ids", []))

    ranked = (
        rank_listings(output, state.get("listing_results", {}), weights, verified) if output else []
    )
    report: dict[str, Any] = {
        "run_id": ctx.run_id,
        "brief_id": ctx.brief_id,
        "ranked": [r.model_dump(mode="json") for r in ranked],
        "weights": weights.model_dump(),
        "formula": FORMULA,
        "critic": critic.get("report") if critic else None,
        "relax_suggestion": output.relax_suggestion if output else None,
        # Surfaced in the Results empty state (e.g. demo-data city coverage).
        "scout_status": (state.get("scout") or {}).get("status"),
        "scout_reason": (state.get("scout") or {}).get("reason"),
        "budget_exceeded": ctx.budget.exceeded,
        "isochrones": await _isochrone_bands(ctx),
        "match_explanations": {
            m.listing.id: m.explanation for m in (output.matches if output else [])
        },
    }
    ranked_dumps: list[dict[str, Any]] = report["ranked"]
    await ctx.bus.publish(
        ctx.run_id,
        "partial_result",
        agent="ranker",
        payload={"ranked": ranked_dumps[:10]},
    )
    return {"report": report}


def build_graph(checkpointer: Any) -> Any:
    graph: StateGraph[RunState] = StateGraph(RunState)
    graph.add_node("scout", scout_node)
    graph.add_node("plan", plan_node)
    graph.add_node("analyze_listing", analyze_listing_node)  # type: ignore[arg-type]
    graph.add_node("critic", critic_node)
    graph.add_node("rank", rank_node)

    graph.add_edge(START, "scout")
    graph.add_edge("scout", "plan")
    graph.add_conditional_edges("plan", fan_out, ["analyze_listing", "critic"])
    graph.add_edge("analyze_listing", "critic")
    graph.add_edge("critic", "rank")
    graph.add_edge("rank", END)
    return graph.compile(checkpointer=checkpointer)


# --- Specialist agent registration (phases 4+) -------------------------------
# Imported here (bottom of module) to avoid circular imports.
from app.agents.commute import commute_agent  # noqa: E402
from app.agents.price import price_agent  # noqa: E402
from app.agents.review import review_agent  # noqa: E402

register_per_listing_agent("commute", commute_agent)
register_per_listing_agent("price", price_agent)
register_per_listing_agent("review", review_agent)
