"""Ranking quality + multi-agent vs single-agent baseline + cost/latency.

10 synthetic personas, each with an ideal top-3 labeled by a transparent
oracle utility computed directly from the deterministic seed data (budget
fit + straight-line proximity + amenity needs) — independent of the system's
own scoring. We measure NDCG@5 of:
  - the full multi-agent ranking (final_score), and
  - a single-agent baseline (Scout match score only, no specialists),
plus red-flag surfacing, per-run cost, and latency percentiles.
"""

import math
import statistics
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.agents.contracts import Place, SearchBriefInput
from app.db import models
from app.db.session import get_session_factory, init_db
from app.graph import runner
from app.graph.context import create_run_context
from app.seed.buildings import BUILDINGS
from app.seed.listings import generate_listings
from app.seed.load import seed
from app.services.geo import haversine_m
from evals.common import SuiteResult

BAD_BUILDINGS = {b.name for b in BUILDINGS if b.profile not in ("clean",)}


@dataclass
class Persona:
    name: str
    brief: SearchBriefInput
    amenity_needs: list[str]
    proximity_weight: float  # how much this persona cares about the commute
    budget_weight: float


def _place(label: str, lat: float, lng: float, tolerance: int = 25) -> Place:
    return Place(
        label=label,
        address=label,
        lat=lat,
        lng=lng,
        weight=1.0,
        modes=["drive", "transit"],
        tolerance_minutes=tolerance,
    )


def personas() -> list[Persona]:
    sc = (37.3541, -121.9552)  # Santa Clara
    mv = (37.3861, -122.0839)  # Mountain View
    sj = (37.3382, -121.8863)  # San Jose
    cu = (37.3230, -122.0322)  # Cupertino
    items: list[Persona] = []

    def add(
        name: str,
        budget: int,
        beds: float,
        cities: list[str],
        place: Place,
        needs: list[str],
        proximity_weight: float,
        budget_weight: float,
        pets: list[str] | None = None,
    ) -> None:
        items.append(
            Persona(
                name=name,
                brief=SearchBriefInput(
                    budget_max=budget,
                    beds=beds,
                    baths=1,
                    cities=cities,
                    pets=pets or [],
                    nice_to_haves=needs,
                    important_places=[place],
                    max_listings=20,
                ),
                amenity_needs=needs,
                proximity_weight=proximity_weight,
                budget_weight=budget_weight,
            )
        )

    add(
        "budget-first grad",
        2300,
        1,
        ["San Jose"],
        _place("SJ office", *sj),
        ["dishwasher"],
        0.2,
        0.7,
    )
    add(
        "dog owner engineer",
        3800,
        2,
        ["Sunnyvale", "Santa Clara"],
        _place("SC office", *sc),
        ["dog friendly", "parking"],
        0.4,
        0.3,
        pets=["dog"],
    )
    add(
        "commute hawk",
        3400,
        1,
        ["Santa Clara", "Sunnyvale"],
        _place("SC campus", *sc, 15),
        [],
        0.8,
        0.1,
    )
    add(
        "family of four",
        4800,
        3,
        ["Cupertino", "San Jose"],
        _place("Cupertino school", *cu),
        ["in-unit laundry"],
        0.4,
        0.3,
    )
    add(
        "mv cyclist",
        3600,
        1,
        ["Mountain View"],
        _place("MV office", *mv, 20),
        ["bike storage"],
        0.6,
        0.2,
    )
    add(
        "amenity maximalist",
        4200,
        2,
        ["Sunnyvale", "Santa Clara", "San Jose"],
        _place("SC office", *sc),
        ["pool", "gym", "ev charging"],
        0.2,
        0.2,
    )
    add("frugal couple", 2900, 2, ["San Jose"], _place("SJ downtown", *sj), ["parking"], 0.3, 0.6)
    add(
        "cat person",
        3100,
        1,
        ["Santa Clara", "San Jose"],
        _place("SC office", *sc),
        ["cat friendly"],
        0.3,
        0.4,
        pets=["cat"],
    )
    add(
        "studio minimalist",
        2200,
        0,
        ["Mountain View", "Sunnyvale"],
        _place("MV office", *mv),
        [],
        0.5,
        0.4,
    )
    add(
        "space seeker",
        4400,
        2,
        ["Cupertino", "Sunnyvale"],
        _place("Cupertino office", *cu),
        ["balcony"],
        0.3,
        0.2,
    )
    return items


def oracle_utility(listing: Any, persona: Persona) -> float:
    """Transparent hand-authored utility; NOT the system's formula."""
    brief = persona.brief
    budget_fit = max(0.0, (brief.budget_max - listing.rent) / brief.budget_max)
    place = brief.important_places[0]
    distance_km = (
        haversine_m(listing.lat or 0, listing.lng or 0, place.lat or 0, place.lng or 0) / 1000
    )
    proximity = max(0.0, 1 - distance_km / 15)
    amenity = sum(1 for need in persona.amenity_needs if need in listing.amenities) / max(
        len(persona.amenity_needs), 1
    )
    sqft_bonus = min((listing.sqft or 700) / 2000, 0.5)
    return (
        persona.budget_weight * budget_fit
        + persona.proximity_weight * proximity
        + 0.25 * amenity
        + 0.1 * sqft_bonus
    )


def ideal_top3(persona: Persona) -> list[str]:
    candidates = [
        listing
        for listing in generate_listings()
        if listing.city in persona.brief.cities
        and listing.beds >= persona.brief.beds
        and listing.rent <= persona.brief.budget_max
        and ("dog" not in persona.brief.pets or "dog friendly" in listing.amenities)
        and (
            "cat" not in persona.brief.pets
            or any(a in listing.amenities for a in ("cat friendly", "dog friendly"))
        )
    ]
    ranked = sorted(candidates, key=lambda c: oracle_utility(c, persona), reverse=True)
    return [c.id for c in ranked[:3]]


def ndcg_at_5(system_order: list[str], ideal: list[str]) -> float:
    relevance = {lid: 3 - i for i, lid in enumerate(ideal)}  # 3, 2, 1
    dcg = sum(
        relevance.get(lid, 0) / math.log2(rank + 2) for rank, lid in enumerate(system_order[:5])
    )
    idcg = sum(
        rel / math.log2(rank + 2)
        for rank, rel in enumerate(sorted(relevance.values(), reverse=True))
    )
    return dcg / idcg if idcg else 0.0


async def run_ranking_eval() -> SuiteResult:
    await init_db()
    await seed()
    factory = get_session_factory()

    ndcg_multi: list[float] = []
    ndcg_single: list[float] = []
    costs: list[float] = []
    latencies: list[float] = []
    cache_rates: list[float] = []
    flag_opportunities = 0
    flags_surfaced = 0

    for persona in personas():
        ideal = ideal_top3(persona)
        async with factory() as session:
            user = (
                await session.execute(
                    select(models.User).where(models.User.email == "evals@leaselens.dev")
                )
            ).scalar_one_or_none()
            if user is None:
                user = models.User(email="evals@leaselens.dev")
                session.add(user)
                await session.flush()
            brief_row = models.SearchBrief(
                user_id=user.id,
                raw_text=persona.name,
                data=persona.brief.model_dump(mode="json"),
            )
            session.add(brief_row)
            await session.flush()
            run = models.Run(brief_id=brief_row.id, user_id=user.id, status="pending")
            session.add(run)
            await session.commit()
            run_id = run.id
            create_run_context(run_id, user.id, brief_row.id, persona.brief)

        started = time.monotonic()
        await runner.launch_run(run_id)
        await runner.wait_for_run(run_id)
        async with factory() as session:
            run_row = (
                await session.execute(select(models.Run).where(models.Run.id == run_id))
            ).scalar_one()
            if run_row.status == "interrupted":
                await runner.resume_run(run_id, {"approve": True})
                await runner.wait_for_run(run_id)
                await session.refresh(run_row)
            latencies.append(time.monotonic() - started)
            report = run_row.result or {}
            costs.append(run_row.cost_usd)
            total_cache = run_row.cache_hits + run_row.cache_misses
            if total_cache:
                cache_rates.append(run_row.cache_hits / total_cache)

        ranked = report.get("ranked", [])
        multi_order = [e["listing_id"] for e in ranked]
        single_order = [
            e["listing_id"]
            for e in sorted(ranked, key=lambda e: e["scores"].get("match") or 0, reverse=True)
        ]
        ndcg_multi.append(ndcg_at_5(multi_order, ideal))
        ndcg_single.append(ndcg_at_5(single_order, ideal))

        # Red-flag surfacing: top-5 listings in known problem buildings should
        # carry a red flag in the multi-agent output; the single agent cannot.
        async with factory() as session:
            for entry in ranked[:5]:
                row = (
                    await session.execute(
                        select(models.Listing).where(models.Listing.id == entry["listing_id"])
                    )
                ).scalar_one_or_none()
                if row is not None and row.building_name in BAD_BUILDINGS:
                    flag_opportunities += 1
                    if entry.get("top_red_flag"):
                        flags_surfaced += 1

    def pctile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(int(q * (len(ordered) - 1)), len(ordered) - 1)
        return ordered[index]

    return SuiteResult(
        name="ranking_and_baseline",
        metrics={
            "personas": len(ndcg_multi),
            "ndcg@5_multi_agent": round(statistics.mean(ndcg_multi), 3),
            "ndcg@5_single_agent_baseline": round(statistics.mean(ndcg_single), 3),
            "red_flag_recall_multi": round(flags_surfaced / max(flag_opportunities, 1), 3),
            "red_flag_recall_single_agent": 0.0,
            "run_latency_s_p50": round(pctile(latencies, 0.5), 2),
            "run_latency_s_p95": round(pctile(latencies, 0.95), 2),
            "run_cost_usd_p50": round(pctile(costs, 0.5), 5),
            "run_cost_usd_p95": round(pctile(costs, 0.95), 5),
            "cache_hit_rate_mean": round(statistics.mean(cache_rates), 3) if cache_rates else 0.0,
        },
        notes=[
            "Single-agent baseline = Scout match score only (one monolithic pass, "
            "no commute/review/price specialists, no critic).",
            "DEMO_MODE numbers are deterministic (mock providers); re-run with real "
            "providers for production figures.",
        ],
    )
