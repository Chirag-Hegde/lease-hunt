"""Lease clause detection eval: precision/recall/F1 per clause type vs the
generated ground truth, plus citation accuracy (page match + bbox overlap)."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.agents.lease import analyze_lease
from app.db import models
from app.db.session import get_session_factory, init_db
from app.seed.leases import SEED_DIR, generate_leases
from evals.common import SuiteResult, bbox_overlap, f1


async def run_lease_eval() -> SuiteResult:
    await init_db()
    manifest = generate_leases()

    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)
    severity_correct = 0
    severity_total = 0
    citations_checked = 0
    citations_page_ok = 0
    citations_bbox_ok = 0
    per_lease: dict[str, Any] = {}

    factory = get_session_factory()
    for entry in manifest:
        async with factory() as session:
            user = (
                await session.execute(
                    select(models.User).where(models.User.email == "evals@leaselens.dev")
                )
            ).scalar_one_or_none()
            if user is None:
                user = models.User(email="evals@leaselens.dev")
                session.add(user)
                await session.flush()
            lease = models.Lease(
                user_id=user.id,
                filename=str(entry["file"]),
                file_path=str(SEED_DIR / str(entry["file"])),
                status="pending",
                purge_after=datetime.now(UTC) + timedelta(days=1),
            )
            session.add(lease)
            await session.commit()
            lease_id = lease.id

        await analyze_lease(lease_id)

        async with factory() as session:
            rows = (
                (
                    await session.execute(
                        select(models.LeaseFinding).where(models.LeaseFinding.lease_id == lease_id)
                    )
                )
                .scalars()
                .all()
            )
        predicted = {
            str(row.clause_type): row for row in rows if row.severity in ("high", "caution", "info")
        }
        expected = {str(f["clause_type"]): f for f in entry["expected_findings"]}  # type: ignore[index]

        lease_tp = 0
        for clause_type, truth in expected.items():
            if clause_type in predicted:
                tp[clause_type] += 1
                lease_tp += 1
                row = predicted[clause_type]
                severity_total += 1
                if row.severity == truth["severity"]:
                    severity_correct += 1
                # Citation accuracy: page match + predicted clause bbox must
                # cover most of the labeled anchor span.
                citations_checked += 1
                citation = row.data["citation"]
                if citation["page"] == truth["page"]:
                    citations_page_ok += 1
                    overlap = bbox_overlap(tuple(citation["bbox"]), tuple(truth["bbox"]))
                    if overlap >= 0.5:
                        citations_bbox_ok += 1
            else:
                fn[clause_type] += 1
        for clause_type in predicted:
            if clause_type not in expected:
                fp[clause_type] += 1

        per_lease[str(entry["key"])] = {
            "expected": len(expected),
            "detected": lease_tp,
            "spurious": sum(1 for c in predicted if c not in expected),
        }

    all_types = sorted(set(tp) | set(fp) | set(fn))
    per_type: dict[str, dict[str, float]] = {}
    for clause_type in all_types:
        precision = tp[clause_type] / max(tp[clause_type] + fp[clause_type], 1)
        recall = tp[clause_type] / max(tp[clause_type] + fn[clause_type], 1)
        per_type[clause_type] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1(precision, recall), 3),
            "support": tp[clause_type] + fn[clause_type],
        }

    total_tp, total_fp, total_fn = sum(tp.values()), sum(fp.values()), sum(fn.values())
    micro_p = total_tp / max(total_tp + total_fp, 1)
    micro_r = total_tp / max(total_tp + total_fn, 1)

    return SuiteResult(
        name="lease_clause_detection",
        metrics={
            "micro_precision": round(micro_p, 3),
            "micro_recall": round(micro_r, 3),
            "micro_f1": round(f1(micro_p, micro_r), 3),
            "severity_accuracy": round(severity_correct / max(severity_total, 1), 3),
            "citation_page_accuracy": round(citations_page_ok / max(citations_checked, 1), 3),
            "citation_bbox_accuracy": round(citations_bbox_ok / max(citations_checked, 1), 3),
            "leases_evaluated": len(manifest),
        },
        details={"per_clause_type": per_type, "per_lease": per_lease},
    )
