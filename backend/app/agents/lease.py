"""Lease agent — the showcase pipeline:

PDF → layout-aware extraction (page + bbox) → clause segmentation → per-clause
classification (fast model) → risk assessment (strong model) grounded in the
jurisdiction rule pack → citations back to exact page/bbox → risk score.
"""

import logging
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.agents.contracts import (
    ClauseType,
    JurisdictionNote,
    LeaseAnalysis,
    LeaseCitation,
    LeaseFindingModel,
    Severity,
)
from app.db import models
from app.db.session import get_session_factory
from app.providers.llm.embeddings import get_embedding_provider
from app.rules.schema import ClauseDefault, JurisdictionRule, load_rule_pack
from app.services.llm import LLMService
from app.services.pdf import ClauseSegment, parse_lease_pdf

logger = logging.getLogger(__name__)

SEVERITY_POINTS: dict[Severity, int] = {"high": 14, "caution": 5, "info": 0}
SEVERITY_ORDER: dict[Severity, int] = {"high": 0, "caution": 1, "info": 2}


class ClauseClassification(BaseModel):
    clause_type: ClauseType


class ClauseRiskAssessment(BaseModel):
    severity: Severity
    explanation: str
    why_it_matters: str
    suggested_ask: str | None = None
    confidence: float = Field(0.7, ge=0.0, le=1.0)


def risk_score(findings: list[LeaseFindingModel]) -> int:
    return min(100, sum(SEVERITY_POINTS[f.severity] for f in findings))


async def _classify(llm: LLMService, segment: ClauseSegment) -> ClauseType:
    result = await llm.call(
        agent="lease",
        task="clause_classify",
        schema=ClauseClassification,
        context={"heading": segment.heading, "text": segment.text},
        heading=segment.heading or "(no heading)",
        text=segment.text[:1500],
    )
    return result.data.clause_type


async def _assess(
    llm: LLMService,
    segment: ClauseSegment,
    clause_type: ClauseType,
    rule: JurisdictionRule | None,
    default: ClauseDefault | None,
) -> ClauseRiskAssessment:
    rule_context = (
        {
            "severity": rule.severity,
            "explanation": rule.explanation,
            "why_it_matters": rule.why_it_matters,
            "suggested_ask": rule.suggested_ask,
            "jurisdiction_note": rule.jurisdiction_note,
        }
        if rule
        else None
    )
    default_context = (
        {
            "severity": default.severity,
            "explanation": default.explanation,
            "why_it_matters": default.why_it_matters,
            "suggested_ask": default.suggested_ask,
        }
        if default
        else None
    )
    result = await llm.call(
        agent="lease",
        task="clause_risk",
        schema=ClauseRiskAssessment,
        context={
            "clause_type": clause_type,
            "text": segment.text,
            "rule": rule_context,
            "default": default_context,
        },
        clause_type=clause_type,
        text=segment.text[:2000],
        rule_context=str(rule_context or default_context or "none"),
        max_tokens=3000,
    )
    return result.data


async def analyze_lease(lease_id: str, state: Literal["california"] = "california") -> None:
    """Run the full pipeline for a stored lease; persists chunks, findings,
    risk score, and status transitions."""
    factory = get_session_factory()
    async with factory() as session:
        lease = (
            await session.execute(select(models.Lease).where(models.Lease.id == lease_id))
        ).scalar_one()
        lease.status = "processing"
        await session.commit()
        file_path = lease.file_path

    try:
        parsed = parse_lease_pdf(file_path)
        llm = LLMService(lease_id=lease_id)
        pack = load_rule_pack(state)
        embedder = get_embedding_provider()

        findings: list[LeaseFindingModel] = []
        for segment in parsed.segments:
            clause_type = await _classify(llm, segment)
            if clause_type == "other":
                continue  # boilerplate (parties, term, signatures)

            rule = next((r for r in pack.rules_for(clause_type) if r.matches(segment.text)), None)
            default = pack.default_for(clause_type)
            if rule is None and default is None:
                continue

            assessment = await _assess(llm, segment, clause_type, rule, default)
            severity: Severity = rule.severity if rule else assessment.severity

            note: JurisdictionNote | None = None
            if rule is not None:
                note = JurisdictionNote(
                    rule_id=rule.id,
                    text=rule.jurisdiction_note,
                    source_url=rule.source_url,
                    verified=rule.verified,
                )

            findings.append(
                LeaseFindingModel(
                    clause_type=clause_type,
                    severity=severity,
                    explanation=assessment.explanation,
                    why_it_matters=assessment.why_it_matters,
                    suggested_ask=assessment.suggested_ask,
                    citation=LeaseCitation(
                        page=segment.page,
                        bbox=segment.bbox,
                        quote=segment.text[:220],
                    ),
                    jurisdiction_note=note,
                    confidence=assessment.confidence
                    if rule is None
                    else max(assessment.confidence, 0.85),
                )
            )

        findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], -f.confidence))
        score = risk_score(findings)
        questions = [
            f.suggested_ask
            for f in findings
            if f.suggested_ask and f.severity in ("high", "caution")
        ]

        embeddings = await embedder.embed([s.text for s in parsed.segments])

        async with factory() as session:
            await session.execute(
                delete(models.LeaseChunk).where(models.LeaseChunk.lease_id == lease_id)
            )
            await session.execute(
                delete(models.LeaseFinding).where(models.LeaseFinding.lease_id == lease_id)
            )
            for segment, vector in zip(parsed.segments, embeddings, strict=True):
                session.add(
                    models.LeaseChunk(
                        lease_id=lease_id,
                        page=segment.page,
                        bbox=list(segment.bbox),
                        heading=segment.heading,
                        text=segment.text,
                        embedding=vector,
                    )
                )
            for finding in findings:
                session.add(
                    models.LeaseFinding(
                        id=finding.id,
                        lease_id=lease_id,
                        clause_type=finding.clause_type,
                        severity=finding.severity,
                        data=finding.model_dump(mode="json"),
                    )
                )
            lease = (
                await session.execute(select(models.Lease).where(models.Lease.id == lease_id))
            ).scalar_one()
            lease.status = "finished"
            lease.page_count = parsed.page_count
            lease.ocr_used = parsed.ocr_used
            lease.risk_score = score
            lease.summary = {
                "counts": {
                    "high": sum(1 for f in findings if f.severity == "high"),
                    "caution": sum(1 for f in findings if f.severity == "caution"),
                    "info": sum(1 for f in findings if f.severity == "info"),
                },
                "questions_for_landlord": questions,
                "rule_pack": f"{pack.state} v{pack.version}",
            }
            await session.commit()
    except Exception as exc:
        logger.exception("lease analysis failed for %s", lease_id)
        async with factory() as session:
            lease = (
                await session.execute(select(models.Lease).where(models.Lease.id == lease_id))
            ).scalar_one()
            lease.status = "failed"
            lease.error = str(exc)[:1000]
            await session.commit()


def analysis_to_contract(
    lease: models.Lease, finding_rows: list[models.LeaseFinding]
) -> LeaseAnalysis:
    findings = [LeaseFindingModel.model_validate(row.data) for row in finding_rows]
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], -f.confidence))
    summary = lease.summary or {}
    return LeaseAnalysis(
        lease_id=lease.id,
        risk_score=lease.risk_score or 0,
        findings=findings,
        page_count=lease.page_count or 0,
        ocr_used=lease.ocr_used,
        questions_for_landlord=list(summary.get("questions_for_landlord", [])),
    )


def utcnow() -> datetime:
    return datetime.now(UTC)
