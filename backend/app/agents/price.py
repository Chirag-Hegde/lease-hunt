"""Price/Comps agent: comparable selection, $/sqft benchmark, percentile,
fair range, and true total monthly cost."""

import statistics
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.agents.contracts import AgentResult, Evidence, Fee, ListingModel, PriceAnalysis
from app.db import models
from app.db.session import get_session_factory
from app.graph.context import RunContext
from app.services.geo import haversine_m
from app.services.mappers import listing_row_to_model

COMP_RADIUS_M = 1.5 * 1609.34
COMP_SQFT_TOLERANCE = 0.20
COMP_MAX_AGE_DAYS = 60
EST_UTILITIES = 120.0  # monthly baseline when utilities aren't bundled

METHOD = (
    "comps: same bedrooms, ≤1.5 mi, listed ≤60 days, sqft ±20% (when known); "
    "percentile = share of comps renting below this unit; fair range = comps "
    "25th–75th percentile; total cost = rent + mandatory monthly fees + "
    "estimated utilities when not bundled"
)


def total_monthly_cost(rent: int, fees: list[Fee]) -> tuple[float, dict[str, float]]:
    breakdown: dict[str, float] = {"rent": float(rent)}
    utilities_bundled = False
    for fee in fees:
        if fee.period != "monthly" or not fee.mandatory:
            continue
        breakdown[fee.name] = fee.amount
        if "utilit" in fee.name.lower():
            utilities_bundled = True
    if not utilities_bundled:
        breakdown["estimated utilities"] = EST_UTILITIES
    return sum(breakdown.values()), breakdown


def select_comps(listing: ListingModel, candidates: list[ListingModel]) -> list[ListingModel]:
    now = datetime.now(UTC)
    comps = []
    for candidate in candidates:
        if candidate.id == listing.id or candidate.beds != listing.beds:
            continue
        if candidate.lat is None or listing.lat is None:
            continue
        if (
            haversine_m(listing.lat, listing.lng or 0, candidate.lat, candidate.lng or 0)
            > COMP_RADIUS_M
        ):
            continue
        if candidate.listed_at is not None:
            listed_at = candidate.listed_at
            if listed_at.tzinfo is None:  # SQLite drops tzinfo; stored as UTC
                listed_at = listed_at.replace(tzinfo=UTC)
            if (now - listed_at) > timedelta(days=COMP_MAX_AGE_DAYS):
                continue
        if listing.sqft and candidate.sqft:
            ratio = candidate.sqft / listing.sqft
            if not (1 - COMP_SQFT_TOLERANCE) <= ratio <= (1 + COMP_SQFT_TOLERANCE):
                continue
        comps.append(candidate)
    return comps


async def price_agent(ctx: RunContext, listing: ListingModel) -> AgentResult[PriceAnalysis]:
    async with get_session_factory()() as session:
        rows = (
            (
                await session.execute(
                    select(models.Listing).where(models.Listing.beds == listing.beds)
                )
            )
            .scalars()
            .all()
        )
    candidates = [listing_row_to_model(row) for row in rows]
    comps = select_comps(listing, candidates)

    total_cost, breakdown = total_monthly_cost(listing.rent, listing.fees)

    if len(comps) < 3:
        return AgentResult[PriceAnalysis](
            agent="price",
            status="unavailable",
            reason=f"only {len(comps)} comparable listings found (need ≥3 for a fair benchmark)",
            confidence=0.0,
        )

    rents = sorted(comp.rent for comp in comps)
    below = sum(1 for rent in rents if rent < listing.rent)
    percentile = round(below / len(rents) * 100, 1)
    quartiles = statistics.quantiles(rents, n=4)
    fair_low, fair_high = int(quartiles[0]), int(quartiles[2])

    ppsf_values = [comp.rent / comp.sqft for comp in comps if comp.sqft]
    median_ppsf = round(statistics.median(ppsf_values), 2) if ppsf_values else None
    listing_ppsf = round(listing.rent / listing.sqft, 2) if listing.sqft else None

    data = PriceAnalysis(
        comp_ids=[comp.id for comp in comps[:30]],
        comp_count=len(comps),
        median_ppsf=median_ppsf,
        listing_ppsf=listing_ppsf,
        percentile=percentile,
        fair_range_low=fair_low,
        fair_range_high=fair_high,
        total_monthly_cost=round(total_cost, 2),
        monthly_cost_breakdown=breakdown,
        method=METHOD,
    )
    evidence = [
        Evidence(
            source_type="computed",
            excerpt=(
                f"{len(comps)} comps for {listing.beds:g}bd near {listing.address}: "
                f"fair range ${fair_low:,}–${fair_high:,}; this unit at the "
                f"{percentile:.0f}th percentile"
            ),
        )
    ] + [
        Evidence(
            source_type="listing",
            source_url=comp.url,
            excerpt=f"comp: {comp.address} — ${comp.rent:,}/mo"
            + (f", {comp.sqft} sqft" if comp.sqft else ""),
        )
        for comp in comps[:5]
    ]
    return AgentResult[PriceAnalysis](
        agent="price",
        status="ok",
        data=data,
        evidence=evidence,
        confidence=min(0.5 + 0.05 * len(comps), 0.95),
    )
