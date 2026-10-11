"""SQLAlchemy models. JSON payload columns hold Pydantic-validated agent
contracts (see app.agents.contracts); relational columns exist for querying."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import EmbeddingVector, PortableJSON

EMBEDDING_DIM = 1536


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {dict[str, Any]: PortableJSON, list[Any]: PortableJSON}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchBrief(Base):
    __tablename__ = "search_briefs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    places: Mapped[list["Place"]] = relationship(back_populates="brief", cascade="all, delete")


class Place(Base):
    __tablename__ = "places"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    brief_id: Mapped[str] = mapped_column(ForeignKey("search_briefs.id"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    modes: Mapped[list[Any]] = mapped_column(PortableJSON, default=list)
    arrival_time: Mapped[str | None] = mapped_column(String(8))
    tolerance_minutes: Mapped[int] = mapped_column(Integer, default=30)

    brief: Mapped[SearchBrief] = relationship(back_populates="places")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    brief_id: Mapped[str] = mapped_column(ForeignKey("search_briefs.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    # pending | running | interrupted | finished | failed | budget_exceeded
    interrupt: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON)
    result: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON)
    error: Mapped[str | None] = mapped_column(Text)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cache_hits: Mapped[int] = mapped_column(Integer, default=0)
    cache_misses: Mapped[int] = mapped_column(Integer, default=0)
    critic_rejections: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (Index("ix_run_events_run_seq", "run_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(40))
    agent: Mapped[str | None] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (Index("ix_listings_lat_lng", "lat", "lng"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(
        String(40), index=True
    )  # demo | rentcast | user_url | user_text
    url: Mapped[str | None] = mapped_column(String(1000))
    address: Mapped[str] = mapped_column(String(500))
    normalized_address: Mapped[str | None] = mapped_column(String(500), index=True)
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    rent: Mapped[int] = mapped_column(Integer, index=True)
    deposit: Mapped[int | None] = mapped_column(Integer)
    fees: Mapped[list[Any]] = mapped_column(
        PortableJSON, default=list
    )  # [{name, amount, period, mandatory}]
    beds: Mapped[float] = mapped_column(Float, index=True)
    baths: Mapped[float] = mapped_column(Float)
    sqft: Mapped[int | None] = mapped_column(Integer)
    amenities: Mapped[list[Any]] = mapped_column(PortableJSON, default=list)
    photos: Mapped[list[Any]] = mapped_column(PortableJSON, default=list)
    available_date: Mapped[str | None] = mapped_column(String(10))
    landlord: Mapped[str | None] = mapped_column(String(200))
    building_name: Mapped[str | None] = mapped_column(String(200), index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ListingSource(Base):
    __tablename__ = "listing_sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    source: Mapped[str] = mapped_column(String(40))
    url: Mapped[str | None] = mapped_column(String(1000))
    external_id: Mapped[str | None] = mapped_column(String(200))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CommuteResult(Base):
    __tablename__ = "commute_results"
    __table_args__ = (Index("ix_commute_results_run_listing", "run_id", "listing_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # AgentResult[CommuteScore]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewSource(Base):
    __tablename__ = "review_sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    building_key: Mapped[str] = mapped_column(String(200), index=True)
    source_type: Mapped[str] = mapped_column(String(20))  # google | reddit | demo
    external_id: Mapped[str | None] = mapped_column(String(200))  # place_id / post id
    url: Mapped[str | None] = mapped_column(String(1000))
    author: Mapped[str | None] = mapped_column(String(120))
    rating: Mapped[float | None] = mapped_column(Float)
    text: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewInsight(Base):
    __tablename__ = "review_insights"
    __table_args__ = (Index("ix_review_insights_run_listing", "run_id", "listing_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # AgentResult[ReviewInsights]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PriceAnalysisRow(Base):
    __tablename__ = "price_analyses"
    __table_args__ = (Index("ix_price_analyses_run_listing", "run_id", "listing_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # AgentResult[PriceAnalysis]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("listings.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    file_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    # pending | processing | finished | failed
    page_count: Mapped[int | None] = mapped_column(Integer)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class LeaseChunk(Base):
    __tablename__ = "lease_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    lease_id: Mapped[str] = mapped_column(ForeignKey("leases.id"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list[Any]] = mapped_column(PortableJSON)  # [x0, y0, x1, y1] in PDF points
    heading: Mapped[str | None] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM))


class LeaseFinding(Base):
    __tablename__ = "lease_findings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    lease_id: Mapped[str] = mapped_column(ForeignKey("leases.id"), index=True)
    clause_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(10), index=True)  # info | caution | high
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # LeaseFinding contract
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NegotiationDraftRow(Base):
    __tablename__ = "negotiation_drafts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    lease_id: Mapped[str | None] = mapped_column(ForeignKey("leases.id"))
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"))
    tone: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # NegotiationDraft contract
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CriticReportRow(Base):
    __tablename__ = "critic_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    listing_id: Mapped[str | None] = mapped_column(ForeignKey("listings.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(PortableJSON)  # CriticReport contract
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    lease_id: Mapped[str | None] = mapped_column(String(32), index=True)
    agent: Mapped[str] = mapped_column(String(40), index=True)
    task: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
