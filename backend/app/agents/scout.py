"""Scout agent: find, dedupe, filter, and score candidate listings."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.agents.contracts import (
    AgentResult,
    Evidence,
    ListingModel,
    ScoutMatch,
    ScoutOutput,
    SearchBriefInput,
)
from app.db import models
from app.db.session import get_session_factory
from app.graph.context import RunContext
from app.services.geo import haversine_m, normalize_address
from app.services.llm import LLMService
from app.services.mappers import listing_model_to_row

DEDUPE_DISTANCE_M = 30.0
DEDUPE_RENT_TOLERANCE = 0.03


def dedupe_listings(listings: list[ListingModel]) -> tuple[list[ListingModel], int]:
    """Cross-source dedupe: normalized address match, or geodistance < 30m with
    same beds and rent within 3%."""
    kept: list[ListingModel] = []
    removed = 0
    seen_addresses: dict[str, int] = {}
    for listing in listings:
        addr = normalize_address(listing.address)
        duplicate_of: ListingModel | None = None
        if addr in seen_addresses:
            duplicate_of = kept[seen_addresses[addr]]
        else:
            for existing in kept:
                if (
                    listing.lat is not None
                    and existing.lat is not None
                    and listing.lng is not None
                    and existing.lng is not None
                    and haversine_m(listing.lat, listing.lng, existing.lat, existing.lng)
                    < DEDUPE_DISTANCE_M
                    and existing.beds == listing.beds
                    and abs(existing.rent - listing.rent) <= existing.rent * DEDUPE_RENT_TOLERANCE
                ):
                    duplicate_of = existing
                    break
        if duplicate_of is not None:
            removed += 1
            continue
        seen_addresses[addr] = len(kept)
        kept.append(listing)
    return kept, removed


def _violates_deal_breakers(listing: ListingModel, brief: SearchBriefInput) -> str | None:
    haystack = " ".join(
        [
            listing.address.lower(),
            " ".join(a.lower() for a in listing.amenities),
            (listing.raw_text or "").lower(),
        ]
    )
    for breaker in brief.deal_breakers:
        if breaker.lower().strip() in haystack:
            return breaker
    if brief.parking_required and not any(
        "parking" in a or "garage" in a for a in listing.amenities
    ):
        return "no parking"
    if brief.in_unit_laundry_required and "in-unit laundry" not in listing.amenities:
        return "no in-unit laundry"
    if "dog" in brief.pets and "dog friendly" not in listing.amenities:
        return "not dog friendly"
    if "cat" in brief.pets and not any(
        a in listing.amenities for a in ("cat friendly", "dog friendly")
    ):
        return "not pet friendly"
    return None


def score_listing(listing: ListingModel, brief: SearchBriefInput) -> ScoutMatch:
    score = 55.0
    reasons: list[str] = []

    # Budget fit: at budget → neutral; each 1% under budget adds; over subtracts.
    budget_delta = (brief.budget_max - listing.rent) / brief.budget_max
    score += max(min(budget_delta * 120, 20), -25)
    if listing.rent <= brief.budget_max:
        reasons.append(f"${listing.rent:,}/mo is within budget")
    else:
        reasons.append(f"${listing.rent:,}/mo is {listing.rent - brief.budget_max:,} over budget")

    matched_must = [
        m for m in brief.must_haves if any(m.lower() in a.lower() for a in listing.amenities)
    ]
    missing_must = [m for m in brief.must_haves if m not in matched_must]
    score += 8 * len(matched_must) - 12 * len(missing_must)
    if matched_must:
        reasons.append("has " + ", ".join(matched_must))
    if missing_must:
        reasons.append("missing " + ", ".join(missing_must))

    matched_nice = [
        n for n in brief.nice_to_haves if any(n.lower() in a.lower() for a in listing.amenities)
    ]
    score += 4 * len(matched_nice)
    if matched_nice:
        reasons.append("bonus: " + ", ".join(matched_nice))

    if listing.beds > brief.beds:
        score += 2
        reasons.append(f"{listing.beds:g} beds (asked {brief.beds:g})")
    if listing.sqft:
        score += min((listing.sqft - 700) / 100, 5)

    return ScoutMatch(
        listing=listing,
        match_score=round(max(min(score, 100.0), 0.0), 1),
        matched_must_haves=matched_must,
        matched_nice_to_haves=matched_nice,
        explanation="; ".join(reasons),
    )


def suggest_relaxation(brief: SearchBriefInput, candidates: int) -> str | None:
    if candidates >= 3:
        return None
    suggestions = []
    suggestions.append(f"raise the budget above ${brief.budget_max:,}")
    if brief.cities and len(brief.cities) < 3:
        suggestions.append("add nearby cities (e.g. San Jose) to the search area")
    if brief.beds >= 2:
        suggestions.append(f"consider {brief.beds - 1:g}-bedroom units")
    if brief.deal_breakers:
        suggestions.append("review your deal-breakers")
    return "Few results — try to " + " or ".join(suggestions[:2])


async def parse_listing_from_text(
    llm: LLMService, text: str, url: str | None = None
) -> ListingModel:
    """LLM-extract a listing a user pasted (tool used by brief/scout flows)."""
    result = await llm.call(
        agent="scout",
        task="listing_extract",
        schema=ListingModel,
        context={"text": text, "url": url},
        text=text[:6000],
    )
    listing = result.data
    listing.source = "user_url" if url else "user_text"
    listing.url = url
    listing.raw_text = text[:6000]
    return listing


async def scout_agent(ctx: RunContext) -> AgentResult[ScoutOutput]:
    brief = ctx.brief

    await ctx.bus.publish(
        ctx.run_id,
        "tool_called",
        agent="scout",
        payload={"tool": "search_listings", "provider": ctx.listings.name},
    )
    async with get_session_factory()() as session:
        candidates = await ctx.listings.search(brief, session)

    deduped, removed = dedupe_listings(candidates)
    await ctx.bus.publish(
        ctx.run_id,
        "tool_called",
        agent="scout",
        payload={"tool": "dedupe_listings", "candidates": len(candidates), "removed": removed},
    )

    filtered: list[ListingModel] = []
    for listing in deduped:
        if _violates_deal_breakers(listing, brief) is None:
            filtered.append(listing)

    matches = sorted(
        (score_listing(listing, brief) for listing in filtered),
        key=lambda m: m.match_score,
        reverse=True,
    )[: brief.max_listings]

    # Persist any listings that came from outside the DB (e.g. rentcast).
    async with get_session_factory()() as session:
        for match in matches:
            exists = (
                await session.execute(
                    select(models.Listing.id).where(models.Listing.id == match.listing.id)
                )
            ).scalar_one_or_none()
            if exists is None:
                session.add(listing_model_to_row(match.listing))
        await session.commit()

    await ctx.bus.publish(
        ctx.run_id,
        "partial_result",
        agent="scout",
        payload={
            "matches": [
                {
                    "listing_id": m.listing.id,
                    "address": m.listing.address,
                    "rent": m.listing.rent,
                    "match_score": m.match_score,
                }
                for m in matches
            ]
        },
    )

    output = ScoutOutput(
        matches=matches,
        total_candidates=len(candidates),
        deduped=removed,
        relax_suggestion=suggest_relaxation(brief, len(matches)),
    )
    evidence = [
        Evidence(
            source_type="listing",
            source_url=m.listing.url,
            excerpt=f"{m.listing.address} — ${m.listing.rent:,}/mo, {m.listing.beds:g}bd/{m.listing.baths:g}ba",
            retrieved_at=datetime.now(UTC),
        )
        for m in matches[:20]
    ]
    status = "ok" if matches else "partial"
    return AgentResult[ScoutOutput](
        agent="scout",
        status=status,
        data=output,
        evidence=evidence,
        confidence=0.95 if matches else 0.4,
        reason=None if matches else "no listings matched the brief",
    )
