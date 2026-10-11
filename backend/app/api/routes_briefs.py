from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.agents.contracts import SearchBriefInput
from app.api.deps import CurrentUser, DbSession
from app.api.schemas import BriefCreateRequest, BriefResponse
from app.db import models
from app.providers.geocode.factory import get_geocoder
from app.services.llm import LLMService

router = APIRouter(prefix="/api/briefs", tags=["briefs"])


async def _geocode_places(brief: SearchBriefInput) -> SearchBriefInput:
    geocoder = get_geocoder()
    for place in brief.important_places:
        if place.lat is None or place.lng is None:
            coords = await geocoder.geocode(place.address)
            if coords:
                place.lat, place.lng = coords
    return brief


@router.post("/parse", response_model=SearchBriefInput)
async def parse_brief_preview(body: BriefCreateRequest, user: CurrentUser) -> SearchBriefInput:
    """Parse natural language into a SearchBrief without persisting (live
    preview in the brief builder)."""
    if not (body.text and body.text.strip()):
        raise HTTPException(422, "provide `text`")
    llm = LLMService()
    result = await llm.call(
        agent="orchestrator",
        task="brief_parse",
        schema=SearchBriefInput,
        context={"text": body.text},
        text=body.text,
    )
    return result.data


@router.post("", response_model=BriefResponse)
async def create_brief(
    body: BriefCreateRequest, user: CurrentUser, session: DbSession
) -> BriefResponse:
    if body.brief is None and not (body.text and body.text.strip()):
        raise HTTPException(422, "provide either `text` or `brief`")

    if body.brief is not None:
        brief = body.brief
    else:
        assert body.text is not None
        llm = LLMService()
        result = await llm.call(
            agent="orchestrator",
            task="brief_parse",
            schema=SearchBriefInput,
            context={"text": body.text},
            text=body.text,
        )
        brief = result.data

    brief = await _geocode_places(brief)

    row = models.SearchBrief(
        user_id=user.id, raw_text=body.text, data=brief.model_dump(mode="json")
    )
    session.add(row)
    await session.flush()
    for place in brief.important_places:
        session.add(
            models.Place(
                brief_id=row.id,
                label=place.label,
                address=place.address,
                lat=place.lat,
                lng=place.lng,
                weight=place.weight,
                modes=list(place.modes),
                arrival_time=place.arrival_time,
                tolerance_minutes=place.tolerance_minutes,
            )
        )
    await session.commit()
    return BriefResponse(id=row.id, raw_text=row.raw_text, data=brief, created_at=row.created_at)


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(brief_id: str, user: CurrentUser, session: DbSession) -> BriefResponse:
    row = (
        await session.execute(
            select(models.SearchBrief).where(
                models.SearchBrief.id == brief_id, models.SearchBrief.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "brief not found")
    return BriefResponse(
        id=row.id,
        raw_text=row.raw_text,
        data=SearchBriefInput.model_validate(row.data),
        created_at=row.created_at,
    )
