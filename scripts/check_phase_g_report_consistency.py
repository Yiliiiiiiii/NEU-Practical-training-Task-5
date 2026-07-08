"""Check consistency across Phase G evaluation reports."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {}
    value = report.get("summary", report)
    return value if isinstance(value, dict) else {}


def build_report(paths: list[Path]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in paths:
        report = _load(path)
        if report is None:
            errors.append(f"missing_or_invalid_report: {path}")
            continue
        summary = _summary(report)
        rows.append(
            {
                "path": str(path),
                "dataset_size": summary.get("dataset_size")
                or summary.get("document_count"),
                "average_recall": summary.get("average_recall")
                or summary.get("mapping_recall_average")
                or summary.get("mapping_recall"),
                "strict_pass_count": summary.get("strict_pass_count"),
                "required_missing_count": summary.get("required_missing_count"),
                "review_required_count": summary.get("review_required_count"),
                "badcase_violations": summary.get("badcase_violation_count")
                or summary.get("badcase_violations"),
                "llm_auto_accepted_count": summary.get("llm_auto_accepted_count"),
                "package_verify_pass_count": summary.get("package_verify_pass_count")
                or summary.get("package_valid_count"),
            }
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if rows and not errors else "failed",
        "report_consistency_passed": bool(rows and not errors),
        "rows": rows,
        "errors": errors,
        "explanations": [
            "Different diagnostic scope, split, or field-level vs candidate-level counts must be interpreted per source report."
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase G Report Consistency",
        "",
        f"- Status: {report['status']}",
        f"- Passed: {report['report_consistency_passed']}",
        "",
        "## Reports",
        "",
        "| Path | Dataset | Recall | Strict pass | Missing | Review required |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['path']} | {row['dataset_size']} | {row['average_recall']} | "
            f"{row['strict_pass_count']} | {row['required_missing_count']} | "
            f"{row['review_required_count']} |"
        )
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("reports", nargs="*", type=Path)
    args = parser.parse_args(argv)
    paths = args.reports or [
        ROOT / "reports" / "phase_g_non_procurement_mapping_eval_report.json",
        ROOT / "reports" / "phase_g_blind_set_eval_report.json",
        ROOT / "reports" / "phase_g_review_judge_scoped_report.json",
    ]
    report = build_report(paths)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
