from typing import Any, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.contracts import ListingModel
from app.api.deps import CurrentUser, DbSession
from app.db import models
from app.services.mappers import listing_row_to_model

router = APIRouter(prefix="/api/listings", tags=["listings"])


class ListingDetail(BaseModel):
    listing: ListingModel
    results: dict[str, Any] = Field(default_factory=dict)  # agent -> latest AgentResult dump
    lease_ids: list[str] = Field(default_factory=list)


@router.get("/{listing_id}", response_model=ListingDetail)
async def get_listing(listing_id: str, user: CurrentUser, session: DbSession) -> ListingDetail:
    row = (
        await session.execute(select(models.Listing).where(models.Listing.id == listing_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "listing not found")

    results: dict[str, Any] = {}
    result_tables: list[
        tuple[
            type[models.CommuteResult] | type[models.ReviewInsight] | type[models.PriceAnalysisRow],
            str,
        ]
    ] = [
        (models.CommuteResult, "commute"),
        (models.ReviewInsight, "review"),
        (models.PriceAnalysisRow, "price"),
    ]
    for table, agent_name in result_tables:
        latest = cast(
            "models.CommuteResult | models.ReviewInsight | models.PriceAnalysisRow | None",
            (
                await session.execute(
                    select(table)
                    .where(table.listing_id == listing_id)
                    .order_by(table.created_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first(),
        )
        if latest is not None:
            results[agent_name] = latest.data

    lease_ids = [
        lease_id
        for (lease_id,) in (
            await session.execute(
                select(models.Lease.id).where(
                    models.Lease.listing_id == listing_id, models.Lease.user_id == user.id
                )
            )
        ).all()
    ]
    return ListingDetail(listing=listing_row_to_model(row), results=results, lease_ids=lease_ids)
