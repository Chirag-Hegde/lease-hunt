"""Graph state. JSON-serializable (checkpointed in SQLite/Postgres); heavy
objects (providers, budget, event bus) live in RunContext instead."""

from typing import Annotated, Any, TypedDict


def merge_listing_results(
    a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Reducer for parallel per-listing fan-out: deep-merge one level."""
    merged = dict(a)
    for listing_id, results in b.items():
        merged[listing_id] = {**merged.get(listing_id, {}), **results}
    return merged


class RunState(TypedDict, total=False):
    run_id: str
    # AgentResult[ScoutOutput] dump
    scout: dict[str, Any] | None
    # listing ids chosen for deep analysis (after human-in-the-loop)
    selected_listing_ids: list[str]
    # listing_id -> {agent_name -> AgentResult dump}
    listing_results: Annotated[dict[str, dict[str, Any]], merge_listing_results]
    # CriticReport dump
    critic: dict[str, Any] | None
    # RunReport dump
    report: dict[str, Any] | None


class ListingTask(TypedDict):
    """Send payload for the per-listing subgraph."""

    run_id: str
    listing_id: str
