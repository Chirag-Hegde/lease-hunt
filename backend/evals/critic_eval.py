"""Critic effectiveness: inject 20 deliberately unsupported claims among
supported ones; measure the % caught (rejected or downgraded) and the false
positive rate on genuinely supported claims."""

import random
from typing import Any

from app.agents.contracts import Place, SearchBriefInput
from app.agents.critic import critic_agent
from app.db.session import init_db
from app.graph.context import create_run_context, release_run_context
from evals.common import SuiteResult

# (claimed theme, supporting evidence?) — unsupported pairs mismatch on purpose.
_THEME_EXCERPTS = {
    "pests": ["Saw roaches in the kitchen twice this month.", "Mice in the garage again."],
    "noise": ["Walls are paper thin, I hear every alarm.", "Freeway noise is constant."],
    "maintenance": ["Work orders take 3 weeks.", "The elevator was broken for a month."],
    "parking": ["Guest parking is a joke.", "They tow aggressively, $450 to get the car."],
    "safety": ["Two car break-ins last month.", "The garage gate has been broken."],
}
_UNRELATED = [
    "The pool is lovely in summer.",
    "Move-in was smooth and the unit matched the photos.",
    "Front office staff remembered my name.",
    "Rent was paid on the first every month.",
]


def _result_with_claim(theme: str, excerpts: list[str], with_urls: bool = True) -> dict[str, Any]:
    evidence = [
        {
            "id": f"e{i}",
            "source_type": "review",
            "source_url": f"https://example.com/r{i}" if with_urls else None,
            "excerpt": excerpt,
        }
        for i, excerpt in enumerate(excerpts)
    ]
    return {
        "review": {
            "agent": "review",
            "status": "ok",
            "data": {
                "building_key": "eval",
                "review_count": len(excerpts),
                "themes": [
                    {
                        "theme": theme,
                        "frequency": len(excerpts),
                        "sentiment": -0.5,
                        "trend": "stable",
                        "recent_spike": False,
                        "evidence_ids": [e["id"] for e in evidence],
                    }
                ],
                "management_score": 50,
                "red_flags": [
                    f"Recurring {theme.replace('_', ' ')} complaints ({len(excerpts)} mentions)"
                ],
                "fake_review_suspicion": False,
                "fake_review_note": None,
            },
            "evidence": evidence,
        }
    }


async def run_critic_eval() -> SuiteResult:
    await init_db()
    rng = random.Random(7)
    themes = list(_THEME_EXCERPTS)

    listing_results: dict[str, dict[str, Any]] = {}
    unsupported_ids: set[str] = set()
    supported_ids: set[str] = set()

    # 20 injected unsupported claims: evidence is unrelated or absent.
    for i in range(20):
        theme = themes[i % len(themes)]
        if i % 3 == 0:
            results = _result_with_claim(theme, [])  # no evidence at all
        elif i % 3 == 1:
            results = _result_with_claim(theme, rng.sample(_UNRELATED, 2))  # wrong topic
        else:
            results = _result_with_claim(theme, rng.sample(_UNRELATED, 2), with_urls=False)
        listing_id = f"bad-{i:02d}"
        listing_results[listing_id] = results
        unsupported_ids.add(listing_id)

    # 15 genuinely supported claims.
    for i in range(15):
        theme = themes[i % len(themes)]
        listing_id = f"good-{i:02d}"
        listing_results[listing_id] = _result_with_claim(theme, _THEME_EXCERPTS[theme])
        supported_ids.add(listing_id)

    ctx = create_run_context(
        "critic-eval",
        "eval-user",
        "eval-brief",
        SearchBriefInput(
            budget_max=3000,
            important_places=[Place(label="W", address="Santa Clara", lat=37.35, lng=-121.95)],
        ),
    )
    try:
        outcome = await critic_agent(ctx, listing_results)
    finally:
        release_run_context("critic-eval")

    caught = 0
    false_positives = 0
    # Claims map 1:1 to listings: a bad listing is caught when NOT verified.
    for listing_id in unsupported_ids:
        if listing_id not in outcome["verified_listing_ids"]:
            caught += 1
    for listing_id in supported_ids:
        if listing_id not in outcome["verified_listing_ids"]:
            false_positives += 1

    return SuiteResult(
        name="critic_effectiveness",
        metrics={
            "injected_unsupported": len(unsupported_ids),
            "caught": caught,
            "catch_rate": round(caught / len(unsupported_ids), 3),
            "supported_claims": len(supported_ids),
            "false_positives": false_positives,
            "false_positive_rate": round(false_positives / len(supported_ids), 3),
            "rejected_total": outcome["report"]["rejected"],
            "downgraded_total": outcome["report"]["downgraded"],
        },
    )
