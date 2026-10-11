"""Lease PDF pipeline: layout-aware extraction with page + bbox coordinates,
heading-based clause segmentation, and an OCR fallback for scanned documents."""

import re
from dataclasses import dataclass, field

import pymupdf

HEADING_RE = re.compile(r"^\s*(\d{1,2}[.)]\s+|[A-Z][A-Z &/'-]{6,}$|ARTICLE\s+|SECTION\s+)")
MIN_TEXT_CHARS_PER_PAGE = 40  # below this we assume a scanned page


@dataclass
class TextBlock:
    page: int  # 1-indexed
    bbox: tuple[float, float, float, float]
    text: str


@dataclass
class ClauseSegment:
    heading: str | None
    text: str
    page: int
    bbox: tuple[float, float, float, float]
    blocks: list[TextBlock] = field(default_factory=list)


@dataclass
class ParsedLease:
    page_count: int
    blocks: list[TextBlock]
    segments: list[ClauseSegment]
    ocr_used: bool


class LeaseTooLargeError(Exception):
    pass


def _union(boxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _extract_blocks(doc: pymupdf.Document) -> tuple[list[TextBlock], bool]:
    blocks: list[TextBlock] = []
    ocr_used = False
    for page_index in range(doc.page_count):
        page = doc[page_index]
        raw_blocks = page.get_text("blocks")
        page_chars = sum(len(b[4].strip()) for b in raw_blocks)
        if page_chars < MIN_TEXT_CHARS_PER_PAGE:
            ocr_blocks = _ocr_page(page, page_index + 1)
            if ocr_blocks:
                blocks.extend(ocr_blocks)
                ocr_used = True
                continue
        for b in raw_blocks:
            text = re.sub(r"\s+", " ", b[4]).strip()
            if not text:
                continue
            blocks.append(
                TextBlock(
                    page=page_index + 1,
                    bbox=(round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)),
                    text=text,
                )
            )
    return blocks, ocr_used


def _ocr_page(page: pymupdf.Page, page_number: int) -> list[TextBlock]:
    """Tesseract fallback for image-only pages; returns [] if unavailable."""
    try:
        tp = page.get_textpage_ocr(dpi=200, full=True)
    except (RuntimeError, AttributeError):
        return []
    text = page.get_text("text", textpage=tp).strip()
    if not text:
        return []
    rect = page.rect
    return [
        TextBlock(
            page=page_number,
            bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
            text=re.sub(r"\s+", " ", text),
        )
    ]


def _looks_like_heading(text: str) -> bool:
    if len(text) > 90:
        return False
    return bool(HEADING_RE.match(text))


def segment_clauses(blocks: list[TextBlock]) -> list[ClauseSegment]:
    """Group blocks into clauses: a heading block starts a new segment."""
    segments: list[ClauseSegment] = []
    current: ClauseSegment | None = None
    for block in blocks:
        if _looks_like_heading(block.text):
            current = ClauseSegment(
                heading=block.text,
                text="",
                page=block.page,
                bbox=block.bbox,
                blocks=[block],
            )
            segments.append(current)
            continue
        if current is None:
            current = ClauseSegment(
                heading=None, text="", page=block.page, bbox=block.bbox, blocks=[block]
            )
            segments.append(current)
        current.blocks.append(block)
        current.text = (current.text + " " + block.text).strip()
        same_page = [b.bbox for b in current.blocks if b.page == current.page]
        current.bbox = _union(same_page)
    return [s for s in segments if len(s.text) > 30 or (s.heading and len(s.blocks) > 1)]


def parse_lease_pdf(path: str, max_pages: int = 100) -> ParsedLease:
    with pymupdf.open(path) as doc:
        if doc.page_count > max_pages:
            raise LeaseTooLargeError(f"{doc.page_count} pages exceeds the {max_pages}-page limit")
        blocks, ocr_used = _extract_blocks(doc)
        page_count = doc.page_count
    segments = segment_clauses(blocks)
    return ParsedLease(page_count=page_count, blocks=blocks, segments=segments, ocr_used=ocr_used)
