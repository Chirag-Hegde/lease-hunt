"""Commute agent: listing × place × mode durations (peak + off-peak), cached
by geohash pair; weighted 0–100 score with a nonlinear over-tolerance penalty."""

import math

from app.agents.contracts import (
    AgentResult,
    CommuteMode,
    CommuteScore,
    Evidence,
    LegEstimate,
    ListingModel,
    Place,
    PlaceCommute,
)
from app.graph.context import RunContext
from app.providers.commute.base import RouteEstimate, TimePeriod
from app.services.cache import get_cache
from app.services.geo import geohash

CACHE_TTL_S = 60 * 60 * 24  # 24h: road/transit timings move slowly

COMMUTE_FORMULA = (
    "per place: 100 − 25·(t/tol)² while t ≤ tol, then 75·e^(−1.4·(t−tol)/tol); "
    "overall = Σ(weight·place_score)/Σ(weight), using the best allowed mode at peak"
)


def place_score(minutes: float, tolerance_minutes: int) -> float:
    """100 at the door, 75 right at tolerance, decaying hard beyond it."""
    tol = max(float(tolerance_minutes), 1.0)
    if minutes <= tol:
        return 100.0 - 25.0 * (minutes / tol) ** 2
    return 75.0 * math.exp(-1.4 * (minutes - tol) / tol)


async def _cached_estimate(
    ctx: RunContext,
    origin: tuple[float, float],
    dest: tuple[float, float],
    mode: CommuteMode,
    period: TimePeriod,
) -> RouteEstimate:
    key = f"commute:{geohash(*origin)}:{geohash(*dest)}:{mode}:{period}"
    cache = get_cache()
    hit = await cache.get(key)
    if hit is not None:
        ctx.cache_hits += 1
        return RouteEstimate(**hit)
    ctx.cache_misses += 1
    estimate = await ctx.commute.estimate(origin, dest, mode, period)
    await cache.set(
        key,
        {
            "minutes": estimate.minutes,
            "transfers": estimate.transfers,
            "reliability_note": estimate.reliability_note,
        },
        ttl_seconds=CACHE_TTL_S,
    )
    return estimate


async def commute_agent(ctx: RunContext, listing: ListingModel) -> AgentResult[CommuteScore]:
    places: list[Place] = [p for p in ctx.brief.important_places if p.lat is not None]
    if listing.lat is None or listing.lng is None or not places:
        return AgentResult[CommuteScore](
            agent="commute",
            status="unavailable",
            reason=(
                "listing has no coordinates"
                if listing.lat is None
                else "no geocoded important places in the brief"
            ),
            confidence=0.0,
        )

    origin = (listing.lat, listing.lng)
    per_place: list[PlaceCommute] = []
    evidence: list[Evidence] = []

    for place in places:
        assert place.lat is not None and place.lng is not None
        dest = (place.lat, place.lng)
        by_mode: dict[CommuteMode, LegEstimate] = {}
        for mode in place.modes:
            try:
                peak = await _cached_estimate(ctx, origin, dest, mode, "peak")
                offpeak = await _cached_estimate(ctx, origin, dest, mode, "offpeak")
            except Exception:
                continue  # mode unavailable from this provider; others may work
            by_mode[mode] = LegEstimate(
                peak_minutes=peak.minutes,
                offpeak_minutes=offpeak.minutes,
                transfers=peak.transfers,
                reliability_note=peak.reliability_note,
            )
        if not by_mode:
            continue
        best_mode = min(by_mode, key=lambda m: by_mode[m].peak_minutes)
        best = by_mode[best_mode]
        per_place.append(
            PlaceCommute(
                place_label=place.label,
                weight=place.weight,
                by_mode=by_mode,
                best_mode=best_mode,
                best_peak_minutes=best.peak_minutes,
            )
        )
        evidence.append(
            Evidence(
                source_type="computed",
                excerpt=(
                    f"{listing.address} → {place.label}: best {best_mode} "
                    f"{best.peak_minutes:.0f} min peak / "
                    f"{best.offpeak_minutes:.0f} min off-peak"
                ),
            )
        )

    if not per_place:
        return AgentResult[CommuteScore](
            agent="commute",
            status="unavailable",
            reason="no commute mode could be estimated for this listing",
            confidence=0.0,
        )

    total_weight = sum(p.weight for p in per_place)
    overall = sum(
        place_score(p.best_peak_minutes, _tolerance(ctx, p)) * p.weight for p in per_place
    )
    overall /= max(total_weight, 0.001)

    data = CommuteScore(
        per_place=per_place,
        overall_score=round(min(max(overall, 0.0), 100.0), 1),
        formula=COMMUTE_FORMULA,
    )
    partial = len(per_place) < len(places)
    return AgentResult[CommuteScore](
        agent="commute",
        status="partial" if partial else "ok",
        data=data,
        evidence=evidence,
        confidence=0.7 if ctx.commute.name == "mock" else 0.9,
        reason="some places could not be estimated" if partial else None,
    )


def _tolerance(ctx: RunContext, place_commute: PlaceCommute) -> int:
    for place in ctx.brief.important_places:
        if place.label == place_commute.place_label:
            return place.tolerance_minutes
    return 30
