from typing import cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.api.schemas import ListingWithResults
from app.db import models
from app.services.mappers import listing_row_to_model

router = APIRouter(prefix="/api/compare", tags=["compare"])


class CompareResponse(BaseModel):
    listings: list[ListingWithResults] = Field(default_factory=list)


@router.get("", response_model=CompareResponse)
async def compare(ids: str, user: CurrentUser, session: DbSession) -> CompareResponse:
    listing_ids = [i.strip() for i in ids.split(",") if i.strip()][:4]
    if len(listing_ids) < 2:
        raise HTTPException(422, "provide 2–4 listing ids, comma separated")

    entries: list[ListingWithResults] = []
    for listing_id in listing_ids:
        row = (
            await session.execute(select(models.Listing).where(models.Listing.id == listing_id))
        ).scalar_one_or_none()
        if row is None:
            continue
        entry = ListingWithResults(listing=listing_row_to_model(row))
        result_tables: list[
            tuple[
                type[models.CommuteResult]
                | type[models.ReviewInsight]
                | type[models.PriceAnalysisRow],
                str,
            ]
        ] = [
            (models.CommuteResult, "commute"),
            (models.ReviewInsight, "review"),
            (models.PriceAnalysisRow, "price"),
        ]
        for table, agent_name in result_tables:
            latest = (
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
            if latest is not None:
                entry.results[agent_name] = cast(
                    "models.CommuteResult | models.ReviewInsight | models.PriceAnalysisRow", latest
                ).data
        lease = (
            (
                await session.execute(
                    select(models.Lease)
                    .where(
                        models.Lease.listing_id == listing_id,
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
        if lease is not None and lease.risk_score is not None:
            entry.results["lease"] = {
                "status": "ok",
                "data": {"risk_score": lease.risk_score, "lease_id": lease.id},
            }
        entries.append(entry)
    return CompareResponse(listings=entries)
