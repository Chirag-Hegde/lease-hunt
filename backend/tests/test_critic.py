"""Critic/Verifier tests, including injected unsupported claims."""

from typing import Any

from httpx import AsyncClient

from app.agents.critic import critic_agent
from app.graph.context import create_run_context, release_run_context
from tests.test_agents import _brief


def _review_results(
    red_flags: list[str],
    themes: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "review": {
            "agent": "review",
            "status": "ok",
            "data": {
                "building_key": "test",
                "review_count": 5,
                "themes": themes,
                "management_score": 50,
                "red_flags": red_flags,
                "fake_review_suspicion": False,
                "fake_review_note": None,
            },
            "evidence": evidence,
        }
    }


async def test_critic_approves_supported_claims(client: AsyncClient) -> None:
    ctx = create_run_context("critic-run-1", "u1", "b1", _brief())
    try:
        results = {
            "l1": _review_results(
                red_flags=["Recurring pests complaints (3 mentions)"],
                themes=[
                    {
                        "theme": "pests",
                        "frequency": 3,
                        "sentiment": -0.5,
                        "trend": "stable",
                        "recent_spike": False,
                        "evidence_ids": ["e1", "e2"],
                    }
                ],
                evidence=[
                    {
                        "id": "e1",
                        "source_type": "review",
                        "source_url": "https://example.com/r1",
                        "excerpt": "Saw roaches in the kitchen twice this month.",
                    },
                    {
                        "id": "e2",
                        "source_type": "reddit",
                        "source_url": "https://example.com/r2",
                        "excerpt": "The mice in the garage are still around.",
                    },
                ],
            )
        }
        outcome = await critic_agent(ctx, results)
        report = outcome["report"]
        assert report["rejected"] == 0
        assert "l1" in outcome["verified_listing_ids"]
        assert outcome["patched_results"] == {}
    finally:
        release_run_context("critic-run-1")


async def test_critic_rejects_injected_unsupported_claim(client: AsyncClient) -> None:
    ctx = create_run_context("critic-run-2", "u1", "b1", _brief())
    try:
        # Injected claim about pests with evidence that talks about parking.
        results = {
            "l1": _review_results(
                red_flags=["Recurring pests complaints (3 mentions)"],
                themes=[
                    {
                        "theme": "pests",
                        "frequency": 3,
                        "sentiment": -0.5,
                        "trend": "stable",
                        "recent_spike": False,
                        "evidence_ids": ["e1"],
                    }
                ],
                evidence=[
                    {
                        "id": "e1",
                        "source_type": "review",
                        "source_url": "https://example.com/r1",
                        "excerpt": "Guest parking is a joke, they tow aggressively.",
                    }
                ],
            )
        }
        outcome = await critic_agent(ctx, results)
        report = outcome["report"]
        assert report["rejected"] >= 1
        assert "l1" not in outcome["verified_listing_ids"]
        # The unsupported red flag was removed from user-facing data.
        patched = outcome["patched_results"]["l1"]["review"]["data"]
        assert patched["red_flags"] == []
        assert ctx.critic_rejections >= 1
    finally:
        release_run_context("critic-run-2")


async def test_critic_rejects_claim_without_evidence(client: AsyncClient) -> None:
    ctx = create_run_context("critic-run-3", "u1", "b1", _brief())
    try:
        results = {
            "l1": _review_results(
                red_flags=["Recurring noise complaints (2 mentions)"],
                themes=[
                    {
                        "theme": "noise",
                        "frequency": 2,
                        "sentiment": -0.4,
                        "trend": "stable",
                        "recent_spike": False,
                        "evidence_ids": [],  # nothing attached
                    }
                ],
                evidence=[],
            )
        }
        outcome = await critic_agent(ctx, results)
        assert outcome["report"]["rejected"] == 1
        reason = outcome["report"]["reviews"][0]["reason"]
        assert "no supporting evidence" in reason
    finally:
        release_run_context("critic-run-3")


async def test_critic_price_math_check(client: AsyncClient) -> None:
    ctx = create_run_context("critic-run-4", "u1", "b1", _brief())
    try:
        bad_price = {
            "price": {
                "agent": "price",
                "status": "ok",
                "data": {
                    "total_monthly_cost": 5000.0,  # doesn't match breakdown
                    "monthly_cost_breakdown": {"rent": 3000.0, "parking": 100.0},
                    "percentile": 50,
                },
                "evidence": [],
            }
        }
        outcome = await critic_agent(ctx, {"l1": bad_price})
        rejected = [r for r in outcome["report"]["reviews"] if r["action"] == "rejected"]
        assert len(rejected) == 1
        assert "breakdown sums to" in rejected[0]["reason"]
    finally:
        release_run_context("critic-run-4")
