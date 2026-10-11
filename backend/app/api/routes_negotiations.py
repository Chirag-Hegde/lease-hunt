from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.contracts import (
    Evidence,
    LeaseFindingModel,
    LeveragePoint,
    NegotiationBundle,
    PriceAnalysis,
    ReviewInsights,
)
from app.agents.negotiator import Length, LeverageContext, draft_negotiations
from app.api.deps import CurrentUser, DbSession
from app.db import models
from app.services.llm import LLMService
from app.services.mappers import listing_row_to_model

router = APIRouter(prefix="/api/negotiations", tags=["negotiations"])


class NegotiationRequest(BaseModel):
    listing_id: str
    lease_id: str | None = None
    selected_leverage_ids: list[str] | None = None
    length: Length = "standard"


class EvidenceDetail(BaseModel):
    excerpt: str | None
    source_url: str | None
    source_type: str


class NegotiationResponse(BaseModel):
    bundle: NegotiationBundle
    all_leverage_points: list[LeveragePoint]
    evidence: dict[str, EvidenceDetail] = Field(default_factory=dict)


async def _latest(session: Any, table: Any, listing_id: str) -> Any:
    return (
        (
            await session.execute(
                select(table)
                .where(table.listing_id == listing_id)
                .order_by(table.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


@router.post("", response_model=NegotiationResponse)
async def create_negotiation(
    body: NegotiationRequest, user: CurrentUser, session: DbSession
) -> NegotiationResponse:
    listing_row = (
        await session.execute(select(models.Listing).where(models.Listing.id == body.listing_id))
    ).scalar_one_or_none()
    if listing_row is None:
        raise HTTPException(404, "listing not found")
    listing = listing_row_to_model(listing_row)

    evidence_map: dict[str, EvidenceDetail] = {}

    price_row = await _latest(session, models.PriceAnalysisRow, body.listing_id)
    price = None
    price_evidence: list[Evidence] = []
    if price_row and price_row.data.get("status") == "ok":
        price = PriceAnalysis.model_validate(price_row.data["data"])
        price_evidence = [Evidence.model_validate(e) for e in price_row.data.get("evidence", [])]

    review_row = await _latest(session, models.ReviewInsight, body.listing_id)
    review = None
    review_evidence: list[Evidence] = []
    if review_row and review_row.data.get("status") in ("ok", "partial"):
        review = ReviewInsights.model_validate(review_row.data["data"])
        review_evidence = [Evidence.model_validate(e) for e in review_row.data.get("evidence", [])]

    for item in price_evidence + review_evidence:
        evidence_map[item.id] = EvidenceDetail(
            excerpt=item.excerpt, source_url=item.source_url, source_type=item.source_type
        )

    # Lease findings: explicit lease, else the latest finished lease for the listing.
    lease_id = body.lease_id
    if lease_id is None:
        lease_row = (
            (
                await session.execute(
                    select(models.Lease)
                    .where(
                        models.Lease.listing_id == body.listing_id,
                        models.Lease.user_id == user.id,
                        models.Lease.status == "finished",
                    )
                    .order_by(models.Lease.created_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        lease_id = lease_row.id if lease_row else None

    lease_findings: list[LeaseFindingModel] = []
    if lease_id:
        rows = (
            (
                await session.execute(
                    select(models.LeaseFinding).where(models.LeaseFinding.lease_id == lease_id)
                )
            )
            .scalars()
            .all()
        )
        lease_findings = [LeaseFindingModel.model_validate(r.data) for r in rows]
        for finding in lease_findings:
            evidence_map[finding.id] = EvidenceDetail(
                excerpt=finding.citation.quote[:200],
                source_url=None,
                source_type="lease_pdf",
            )

    ctx = LeverageContext(
        listing=listing,
        price=price,
        price_evidence=price_evidence,
        review=review,
        review_evidence=review_evidence,
        lease_findings=lease_findings,
    )
    llm = LLMService()
    bundle, all_points = await draft_negotiations(
        llm, ctx, selected_leverage_ids=body.selected_leverage_ids, length=body.length
    )

    for draft in bundle.drafts:
        session.add(
            models.NegotiationDraftRow(
                user_id=user.id,
                listing_id=body.listing_id,
                lease_id=lease_id,
                tone=draft.tone,
                data=draft.model_dump(mode="json"),
            )
        )
    await session.commit()

    evidence_map["computed-price"] = EvidenceDetail(
        excerpt="Derived from the comparable-listings analysis",
        source_url=None,
        source_type="computed",
    )
    evidence_map["computed-days-on-market"] = EvidenceDetail(
        excerpt="Derived from the listing's posted date", source_url=None, source_type="computed"
    )
    return NegotiationResponse(bundle=bundle, all_leverage_points=all_points, evidence=evidence_map)
