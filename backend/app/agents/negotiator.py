"""Negotiator agent: builds evidence-linked leverage points from the other
agents' verified outputs and drafts three tone variants. Never sends email —
the studio only offers Copy and a mailto link."""

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from app.agents.contracts import (
    Ask,
    Evidence,
    LeaseFindingModel,
    LeveragePoint,
    ListingModel,
    NegotiationBundle,
    NegotiationDraft,
    PriceAnalysis,
    ReviewInsights,
    Tone,
)
from app.services.llm import LLMService

Length = Literal["short", "standard", "long"]


def _point_id(kind: str, text: str) -> str:
    """Deterministic id so chip selections survive regeneration."""
    return hashlib.sha1(f"{kind}|{text}".encode()).hexdigest()[:12]


TONES: tuple[Tone, ...] = ("friendly", "firm", "data-driven")


class DraftText(BaseModel):
    subject: str
    body: str


class LeverageContext(BaseModel):
    """Everything leverage points are built from."""

    listing: ListingModel
    price: PriceAnalysis | None = None
    price_evidence: list[Evidence] = []
    review: ReviewInsights | None = None
    review_evidence: list[Evidence] = []
    lease_findings: list[LeaseFindingModel] = []


def build_leverage_points(ctx: LeverageContext) -> tuple[list[LeveragePoint], list[Ask]]:
    points: list[LeveragePoint] = []
    asks: list[Ask] = []
    listing = ctx.listing

    if ctx.price is not None:
        price_ids = [e.id for e in ctx.price_evidence] or ["computed-price"]
        if ctx.price.percentile >= 55:
            points.append(
                LeveragePoint(
                    text=(
                        f"The unit is priced above {ctx.price.percentile:.0f}% of "
                        f"{ctx.price.comp_count} comparable listings; the fair range is "
                        f"${ctx.price.fair_range_low:,}–${ctx.price.fair_range_high:,}."
                    ),
                    evidence_ids=price_ids,
                    kind="price",
                )
            )
            target = max(ctx.price.fair_range_high, ctx.price.fair_range_low)
            if target < listing.rent:
                asks.append(
                    Ask(
                        kind="rent_reduction",
                        text=f"Reduce rent from ${listing.rent:,} to ${target:,}/mo (top of the comp range)",
                    )
                )
        one_time_fees = [f for f in listing.fees if f.period == "one_time" and f.mandatory]
        for fee in one_time_fees:
            points.append(
                LeveragePoint(
                    text=f"The ${fee.amount:.0f} {fee.name} is a one-time charge other buildings waive to close.",
                    evidence_ids=price_ids,
                    kind="price",
                )
            )
            asks.append(Ask(kind="waived_fee", text=f"Waive the {fee.name} (${fee.amount:.0f})"))
        parking = next(
            (f for f in listing.fees if "parking" in f.name.lower() and f.amount > 0), None
        )
        if parking is not None:
            asks.append(
                Ask(
                    kind="free_parking",
                    text=f"Include parking (currently ${parking.amount:.0f}/mo)",
                )
            )

    if ctx.review is not None and ctx.review.red_flags:
        review_ids = [e.id for e in ctx.review_evidence]
        if review_ids:
            flags = "; ".join(ctx.review.red_flags[:2]).lower()
            points.append(
                LeveragePoint(
                    text=f"Public reviews show {flags} — factors a fair price should reflect.",
                    evidence_ids=review_ids,
                    kind="reputation",
                )
            )

    for finding in ctx.lease_findings:
        if finding.severity in ("high", "caution") and finding.suggested_ask:
            points.append(
                LeveragePoint(
                    text=(
                        f"Lease §({finding.clause_type.replace('_', ' ')}): {finding.explanation}"
                    ),
                    evidence_ids=[finding.id],
                    kind="lease",
                )
            )
            asks.append(Ask(kind="clause_redline", text=finding.suggested_ask))

    if listing.listed_at is not None:
        listed_at = listing.listed_at
        if listed_at.tzinfo is None:
            listed_at = listed_at.replace(tzinfo=UTC)
        days_on_market = (datetime.now(UTC) - listed_at).days
        if days_on_market >= 21:
            points.append(
                LeveragePoint(
                    text=f"The listing has been on the market for {days_on_market} days — vacancy costs the landlord ~${listing.rent / 30:.0f}/day.",
                    evidence_ids=["computed-days-on-market"],
                    kind="timing",
                )
            )

    for point in points:
        point.id = _point_id(point.kind, point.text)
    return points, asks


async def draft_negotiations(
    llm: LLMService,
    ctx: LeverageContext,
    selected_leverage_ids: list[str] | None = None,
    tones: tuple[Tone, ...] = TONES,
    length: Length = "standard",
) -> tuple[NegotiationBundle, list[LeveragePoint]]:
    all_points, asks = build_leverage_points(ctx)
    points = (
        [p for p in all_points if p.id in set(selected_leverage_ids)]
        if selected_leverage_ids is not None
        else all_points
    )
    # Keep only asks still backed by a surviving leverage point kind.
    surviving_kinds = {p.kind for p in points}
    kind_for_ask = {
        "rent_reduction": "price",
        "waived_fee": "price",
        "free_parking": "price",
        "clause_redline": "lease",
        "lease_term": "market",
        "move_in_date": "timing",
    }
    filtered_asks = [a for a in asks if kind_for_ask.get(a.kind, "price") in surviving_kinds]

    drafts: list[NegotiationDraft] = []
    for tone in tones:
        result = await llm.call(
            agent="negotiator",
            task="negotiation_draft",
            schema=DraftText,
            context={
                "tone": tone,
                "length": length,
                "listing": ctx.listing.model_dump(mode="json"),
                "leverage": [p.text for p in points],
                "asks": [a.text for a in filtered_asks],
            },
            tone=tone,
            length=length,
            address=ctx.listing.address,
            rent=ctx.listing.rent,
            leverage="\n".join(f"- {p.text}" for p in points) or "- (none selected)",
            asks="\n".join(f"- {a.text}" for a in filtered_asks) or "- (none)",
            max_tokens=1200,
        )
        drafts.append(
            NegotiationDraft(
                tone=tone,
                subject=result.data.subject,
                body=result.data.body,
                leverage_points=points,
                asks=filtered_asks,
            )
        )
    return NegotiationBundle(listing_id=ctx.listing.id, drafts=drafts), all_points
