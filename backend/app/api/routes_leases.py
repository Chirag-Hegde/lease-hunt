import asyncio
import shutil
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.agents.contracts import LeaseAnalysis
from app.agents.lease import analysis_to_contract, analyze_lease
from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.db import models
from app.seed.leases import SEED_DIR

router = APIRouter(prefix="/api/leases", tags=["leases"])

_tasks: dict[str, asyncio.Task[None]] = {}


class LeaseResponse(BaseModel):
    id: str
    filename: str
    listing_id: str | None
    status: str
    page_count: int | None
    ocr_used: bool
    risk_score: int | None
    summary: dict[str, Any] | None
    error: str | None
    created_at: datetime
    analysis: LeaseAnalysis | None = None


class SampleLease(BaseModel):
    key: str
    title: str
    building_key: str


class SampleList(BaseModel):
    samples: list[SampleLease] = Field(default_factory=list)


def _start_analysis(lease_id: str) -> None:
    task = asyncio.create_task(analyze_lease(lease_id))
    _tasks[lease_id] = task
    task.add_done_callback(lambda _: _tasks.pop(lease_id, None))


async def wait_for_lease(lease_id: str) -> None:
    """Test helper."""
    task = _tasks.get(lease_id)
    if task is not None:
        await task


async def _lease_response(
    lease: models.Lease, session: DbSession, include_analysis: bool
) -> LeaseResponse:
    analysis = None
    if include_analysis and lease.status == "finished":
        rows = (
            (
                await session.execute(
                    select(models.LeaseFinding).where(models.LeaseFinding.lease_id == lease.id)
                )
            )
            .scalars()
            .all()
        )
        analysis = analysis_to_contract(lease, list(rows))
    return LeaseResponse(
        id=lease.id,
        filename=lease.filename,
        listing_id=lease.listing_id,
        status=lease.status,
        page_count=lease.page_count,
        ocr_used=lease.ocr_used,
        risk_score=lease.risk_score,
        summary=lease.summary,
        error=lease.error,
        created_at=lease.created_at,
        analysis=analysis,
    )


@router.post("", response_model=LeaseResponse)
async def upload_lease(
    file: UploadFile,
    user: CurrentUser,
    session: DbSession,
    listing_id: str | None = None,
) -> LeaseResponse:
    settings = get_settings()
    if file.content_type not in (
        "application/pdf",
        "application/x-pdf",
        "application/octet-stream",
    ):
        raise HTTPException(415, "only PDF uploads are accepted")
    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            413, f"file exceeds {settings.max_upload_bytes // (1024 * 1024)}MB limit"
        )
    if not contents.startswith(b"%PDF"):
        raise HTTPException(415, "file is not a valid PDF")

    lease = models.Lease(
        user_id=user.id,
        listing_id=listing_id,
        filename=file.filename or "lease.pdf",
        file_path="",
        status="pending",
        purge_after=datetime.now(UTC) + timedelta(days=settings.lease_retention_days),
    )
    session.add(lease)
    await session.flush()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / f"{lease.id}.pdf"
    dest.write_bytes(contents)
    lease.file_path = str(dest)
    await session.commit()

    _start_analysis(lease.id)
    return await _lease_response(lease, session, include_analysis=False)


@router.get("/samples", response_model=SampleList)
async def list_samples() -> SampleList:
    manifest_path = SEED_DIR / "manifest.json"
    if not manifest_path.exists():
        return SampleList()
    import json

    manifest = json.loads(manifest_path.read_text())
    return SampleList(
        samples=[
            SampleLease(key=m["key"], title=m["title"], building_key=m["building_key"])
            for m in manifest
        ]
    )


@router.post("/samples/{key}", response_model=LeaseResponse)
async def analyze_sample(
    key: str, user: CurrentUser, session: DbSession, listing_id: str | None = None
) -> LeaseResponse:
    source = SEED_DIR / f"{key}.pdf"
    if not source.exists() or "/" in key or ".." in key:
        raise HTTPException(404, "sample lease not found — run `make seed` first")
    settings = get_settings()
    lease = models.Lease(
        user_id=user.id,
        listing_id=listing_id,
        filename=f"{key}.pdf",
        file_path="",
        status="pending",
        purge_after=datetime.now(UTC) + timedelta(days=settings.lease_retention_days),
    )
    session.add(lease)
    await session.flush()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / f"{lease.id}.pdf"
    shutil.copyfile(source, dest)
    lease.file_path = str(dest)
    await session.commit()

    _start_analysis(lease.id)
    return await _lease_response(lease, session, include_analysis=False)


@router.get("", response_model=list[LeaseResponse])
async def list_leases(user: CurrentUser, session: DbSession) -> list[LeaseResponse]:
    rows = (
        (
            await session.execute(
                select(models.Lease)
                .where(models.Lease.user_id == user.id)
                .order_by(models.Lease.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [await _lease_response(row, session, include_analysis=False) for row in rows]


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(lease_id: str, user: CurrentUser, session: DbSession) -> LeaseResponse:
    lease = (
        await session.execute(
            select(models.Lease).where(models.Lease.id == lease_id, models.Lease.user_id == user.id)
        )
    ).scalar_one_or_none()
    if lease is None:
        raise HTTPException(404, "lease not found")
    return await _lease_response(lease, session, include_analysis=True)


@router.get("/{lease_id}/file")
async def get_lease_file(lease_id: str, user: CurrentUser, session: DbSession) -> FileResponse:
    lease = (
        await session.execute(
            select(models.Lease).where(models.Lease.id == lease_id, models.Lease.user_id == user.id)
        )
    ).scalar_one_or_none()
    file_exists = (
        lease is not None
        and lease.file_path
        and await asyncio.to_thread(Path(lease.file_path).exists)
    )
    if lease is None or not file_exists:
        raise HTTPException(404, "lease file not found")
    return FileResponse(lease.file_path, media_type="application/pdf", filename=lease.filename)


@router.delete("/{lease_id}", status_code=204)
async def delete_lease(lease_id: str, user: CurrentUser, session: DbSession) -> None:
    lease = (
        await session.execute(
            select(models.Lease).where(models.Lease.id == lease_id, models.Lease.user_id == user.id)
        )
    ).scalar_one_or_none()
    if lease is None:
        raise HTTPException(404, "lease not found")
    await _purge_lease(lease, session)
    await session.commit()


async def _purge_lease(lease: models.Lease, session: DbSession) -> None:
    if lease.file_path:
        await asyncio.to_thread(partial(Path(lease.file_path).unlink, missing_ok=True))
    await session.execute(delete(models.LeaseChunk).where(models.LeaseChunk.lease_id == lease.id))
    await session.execute(
        delete(models.LeaseFinding).where(models.LeaseFinding.lease_id == lease.id)
    )
    await session.execute(
        delete(models.NegotiationDraftRow).where(models.NegotiationDraftRow.lease_id == lease.id)
    )
    await session.delete(lease)


async def purge_expired_leases() -> int:
    """Delete leases past their retention window (called at startup)."""
    from app.db.session import get_session_factory

    count = 0
    async with get_session_factory()() as session:
        expired = (
            (
                await session.execute(
                    select(models.Lease).where(models.Lease.purge_after < datetime.now(UTC))
                )
            )
            .scalars()
            .all()
        )
        for lease in expired:
            await _purge_lease(lease, session)
            count += 1
        await session.commit()
    return count
