"""Eval CLI: `python -m evals.run --suite all [--ci]`.

Writes markdown + JSON reports to evals/reports/ and, with --ci, fails when
lease clause F1 regresses more than 5 points from the stored baseline.
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from typing import Any

from evals.common import BASELINE_PATH, REPORTS_DIR, SuiteResult, setup_eval_env

F1_REGRESSION_BUDGET = 0.05  # 5 points


async def _run_suites(which: str) -> list[SuiteResult]:
    # Import after env setup so config picks up the isolated database.
    from evals.critic_eval import run_critic_eval
    from evals.lease_eval import run_lease_eval
    from evals.ranking_eval import run_ranking_eval

    results: list[SuiteResult] = []
    if which in ("all", "lease"):
        results.append(await run_lease_eval())
    if which in ("all", "critic"):
        results.append(await run_critic_eval())
    if which in ("all", "ranking"):
        results.append(await run_ranking_eval())
    return results


def _to_markdown(results: list[SuiteResult]) -> str:
    lines = [
        "# Lease Hunt eval report",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} · DEMO_MODE (deterministic mock providers)",
        "",
    ]
    for result in results:
        lines.append(f"## {result.name}")
        lines.append("")
        lines.append("| metric | value |")
        lines.append("|---|---|")
        for key, value in result.metrics.items():
            lines.append(f"| {key} | {value} |")
        lines.append("")
        per_type = result.details.get("per_clause_type")
        if per_type:
            lines.append("### per clause type")
            lines.append("")
            lines.append("| clause type | precision | recall | f1 | support |")
            lines.append("|---|---|---|---|---|")
            for clause_type, m in sorted(per_type.items()):
                lines.append(
                    f"| {clause_type} | {m['precision']} | {m['recall']} | {m['f1']} | {m['support']} |"
                )
            lines.append("")
        for note in result.notes:
            lines.append(f"> {note}")
            lines.append("")
    return "\n".join(lines)


def _ci_gate(results: list[SuiteResult]) -> int:
    lease = next((r for r in results if r.name == "lease_clause_detection"), None)
    if lease is None:
        return 0
    current_f1 = float(lease.metrics["micro_f1"])
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text())
        baseline_f1 = float(baseline.get("lease_micro_f1", 0))
        if current_f1 < baseline_f1 - F1_REGRESSION_BUDGET:
            print(
                f"CI GATE FAILED: lease micro F1 {current_f1:.3f} dropped more than "
                f"{F1_REGRESSION_BUDGET * 100:.0f} points below baseline {baseline_f1:.3f}"
            )
            return 1
        print(f"CI gate ok: lease micro F1 {current_f1:.3f} (baseline {baseline_f1:.3f})")
    else:
        BASELINE_PATH.write_text(json.dumps({"lease_micro_f1": current_f1}, indent=2))
        print(f"wrote new baseline: lease micro F1 {current_f1:.3f}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lease Hunt eval suite")
    parser.add_argument("--suite", default="all", choices=["all", "lease", "critic", "ranking"])
    parser.add_argument("--ci", action="store_true", help="enforce the F1 regression gate")
    args = parser.parse_args()

    setup_eval_env()
    results = asyncio.run(_run_suites(args.suite))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "demo/mock",
        "suites": {r.name: {"metrics": r.metrics, "details": r.details} for r in results},
    }
    (REPORTS_DIR / "report.json").write_text(json.dumps(payload, indent=2))
    markdown = _to_markdown(results)
    (REPORTS_DIR / "report.md").write_text(markdown)
    print(markdown)
    print(f"\nreports written to {REPORTS_DIR}")

    if args.ci:
        sys.exit(_ci_gate(results))


if __name__ == "__main__":
    main()
