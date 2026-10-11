"""Shared eval harness: isolated offline environment + result types."""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "evals" / "reports"
BASELINE_PATH = Path(__file__).resolve().parent / "baselines.json"


def setup_eval_env() -> None:
    """Isolated SQLite DB + mock providers so evals are deterministic."""
    tmp = Path(tempfile.mkdtemp(prefix="leaselens-evals-"))
    os.environ["DEMO_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp}/evals.sqlite3"
    os.environ.pop("REDIS_URL", None)


@dataclass
class SuiteResult:
    name: str
    metrics: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def bbox_overlap(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> float:
    """Intersection area / area of b (the ground-truth anchor box)."""
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    b_area = max((b[2] - b[0]) * (b[3] - b[1]), 1e-6)
    return inter / b_area
