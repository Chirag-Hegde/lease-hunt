"""Generate the 6 demo lease PDFs (reportlab) + ground-truth labels JSON.

Ground truth per lease: expected findings with clause_type, severity, quote,
and the page/bbox located by re-parsing the generated PDF with PyMuPDF — so
the eval suite can score citation accuracy honestly.
"""

import json
from pathlib import Path
from typing import Any

import pymupdf as fitz
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.seed.lease_clauses import CLAUSES, LEASE_SPECS

SEED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "seed" / "generated" / "leases"

_HEADING_STYLE = ParagraphStyle(
    "ClauseHeading", fontName="Helvetica-Bold", fontSize=11, spaceAfter=6, spaceBefore=10
)
_BODY_STYLE = ParagraphStyle(
    "ClauseBody", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=4
)
_TITLE_STYLE = ParagraphStyle("LeaseTitle", fontName="Helvetica-Bold", fontSize=14, spaceAfter=18)


def _build_pdf(path: Path, title: str, rent: int, clause_keys: list[str]) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title=title,
    )
    story: list[Any] = [Paragraph(title, _TITLE_STYLE)]
    story.append(
        Paragraph(
            f"Monthly Rent: ${rent:,}.00 &nbsp;&nbsp;|&nbsp;&nbsp; Governing law: California",
            _BODY_STYLE,
        )
    )
    story.append(Spacer(1, 10))
    for key in clause_keys:
        clause = CLAUSES[key]
        story.append(Paragraph(clause.heading, _HEADING_STYLE))
        story.append(Paragraph(clause.text, _BODY_STYLE))
    story.append(Spacer(1, 24))
    story.append(
        Paragraph(
            "IN WITNESS WHEREOF, the parties have executed this lease. "
            "Landlord: ______________________  Tenant: ______________________  Date: ____________",
            _BODY_STYLE,
        )
    )
    doc.build(story)


def _locate_anchor(pdf_path: Path, anchor: str) -> tuple[int, tuple[float, float, float, float]]:
    """Find (1-indexed page, union bbox) of an anchor phrase in the PDF."""
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            rects = page.search_for(anchor)
            if rects:
                x0 = min(r.x0 for r in rects)
                y0 = min(r.y0 for r in rects)
                x1 = max(r.x1 for r in rects)
                y1 = max(r.y1 for r in rects)
                return page_index + 1, (round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))
    raise ValueError(f"anchor not found in {pdf_path.name}: {anchor!r}")


def generate_leases(out_dir: Path | None = None) -> list[dict[str, Any]]:
    out = out_dir or SEED_DIR
    out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    for key, spec in LEASE_SPECS.items():
        pdf_path = out / f"{key}.pdf"
        clause_keys = spec.clauses
        _build_pdf(pdf_path, spec.title, spec.rent, clause_keys)

        findings = []
        for clause_key in clause_keys:
            clause = CLAUSES[clause_key]
            if clause.clause_type is None:
                continue
            page, bbox = _locate_anchor(pdf_path, clause.anchor)
            findings.append(
                {
                    "clause_type": clause.clause_type,
                    "severity": clause.severity,
                    "quote": clause.anchor,
                    "page": page,
                    "bbox": list(bbox),
                }
            )
        entry = {
            "key": key,
            "file": pdf_path.name,
            "title": spec.title,
            "building_key": spec.building_key,
            "rent": spec.rent,
            "expected_findings": findings,
        }
        manifest.append(entry)
        (out / f"{key}.labels.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    generated = generate_leases()
    print(f"generated {len(generated)} leases in {SEED_DIR}")
