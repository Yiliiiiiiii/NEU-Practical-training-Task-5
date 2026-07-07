"""Evaluate mapping recall for real non-procurement documents."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eval_non_procurement_doc import (  # noqa: E402
    CATALOGS,
    _aggregate,
    _document,
    non_procurement_rows,
)
from eval_real_world_mapping import evaluate_rows  # noqa: E402
from eval_support import (  # noqa: E402
    EvaluationHttpClient,
    load_jsonl,
    write_json,
    write_markdown,
)
from phase_c_report_metadata import attach_run_metadata  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_BASELINE = ROOT / "reports" / "non_procurement_baseline_report.json"
DEFAULT_JSON = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "non_procurement_mapping_eval_report.md"


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _metric(item: dict[str, Any], key: str, default: int | float = 0) -> int | float:
    metrics = item.get("metrics", {})
    if not isinstance(metrics, dict):
        return default
    value = metrics.get(key, default)
    return value if isinstance(value, int | float) else default


def _list(item: dict[str, Any], key: str) -> list[Any]:
    value = item.get(key, [])
    return value if isinstance(value, list) else []


def _target_counts(documents: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"mapped_or_review_count": 0, "missing_required_count": 0}
    )
    for item in documents:
        for target in _list(item, "mapped_or_review_targets"):
            if isinstance(target, str) and target:
                counts[target]["mapped_or_review_count"] += 1
        for target in _list(item, "required_missing"):
            if isinstance(target, str) and target:
                counts[target]["missing_required_count"] += 1
    return dict(sorted(counts.items()))


def build_evaluation_report(
    items: list[dict[str, Any]],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    documents = [_document(item) for item in items]
    aggregate = _aggregate(documents)
    summary = {
        "dataset_size": aggregate["document_count"],
        "strict_pass_count": aggregate["strict_pass_count"],
        "strict_pass_rate": aggregate["strict_pass_rate"],
        "average_recall": aggregate["mapping_recall_average"],
        "review_required_count": aggregate["review_required_count"],
        "required_missing_count": aggregate["required_missing_count"],
        "badcase_violation_count": aggregate["badcase_violation_count"],
        "package_verify_pass_count": aggregate["package_valid_count"],
    }
    by_doc_type = {
        doc_type: _aggregate(
            [item for item in documents if item.get("doc_type") == doc_type]
        )
        for doc_type in CATALOGS
    }
    by_field = _target_counts(documents)
    failed_cases = [
        {
            "doc_id": item.get("doc_id"),
            "doc_type": item.get("doc_type"),
            "reasons": item.get("failure_reasons", []),
        }
        for item in documents
        if item.get("failure_reasons")
    ]
    remaining_gaps = [
        {
            "doc_id": item.get("doc_id"),
            "doc_type": item.get("doc_type"),
            "required_missing": item.get("required_missing", []),
            "review_required_count": len(_list(item, "review_evidence")),
            "failure_reasons": item.get("failure_reasons", []),
        }
        for item in documents
        if item.get("required_missing") or item.get("failure_reasons")
    ]
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "by_doc_type": by_doc_type,
        "by_field": by_field,
        "typical_improvements": [],
        "remaining_gaps": remaining_gaps,
        "failed_cases": failed_cases,
        "documents": documents,
    }
    if baseline:
        report["delta"] = {
            "average_recall": round(
                summary["average_recall"] - float(baseline.get("average_recall", 0.0)),
                3,
            ),
            "review_required_count": summary["review_required_count"]
            - int(baseline.get("review_required_count", 0)),
            "required_missing_count": summary["required_missing_count"]
            - int(baseline.get("required_missing_count", 0)),
            "strict_pass_count": summary["strict_pass_count"]
            - int(baseline.get("strict_pass_count", 0)),
        }
    return report


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Baseline must be an object: {path}")
    return value


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Non-procurement Mapping Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Dataset size: {summary['dataset_size']}",
        f"- Strict pass: {summary['strict_pass_count']}",
        f"- Average recall: {summary['average_recall']:.3f}",
        f"- Review required: {summary['review_required_count']}",
        f"- Required missing: {summary['required_missing_count']}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        f"- Package verification pass: {summary['package_verify_pass_count']}",
    ]
    if "delta" in report:
        delta = report["delta"]
        lines.extend(
            [
                "",
                "## Baseline Delta",
                "",
                f"- Average recall: {delta['average_recall']:+.3f}",
                f"- Review required: {delta['review_required_count']:+d}",
                f"- Required missing: {delta['required_missing_count']:+d}",
                f"- Strict pass: {delta['strict_pass_count']:+d}",
            ]
        )
    lines.extend(
        [
            "",
            "## Metrics By Document Type",
            "",
            "| Type | Documents | Strict pass | Recall avg | Review required | Required missing |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for doc_type, metrics in report["by_doc_type"].items():
        lines.append(
            f"| {markdown_cell(doc_type)} | {metrics['document_count']} | "
            f"{metrics['strict_pass_count']} | "
            f"{metrics['mapping_recall_average']:.3f} | "
            f"{metrics['review_required_count']} | "
            f"{metrics['required_missing_count']} |"
        )
    lines.extend(
        [
            "",
            "## Field-level Recall",
            "",
            "| Field | Mapped or review | Required missing |",
            "| --- | ---: | ---: |",
        ]
    )
    for field, metrics in report["by_field"].items():
        lines.append(
            f"| {markdown_cell(field)} | {metrics['mapped_or_review_count']} | "
            f"{metrics['missing_required_count']} |"
        )
    lines.extend(["", "## Strict Validation", ""])
    if report["failed_cases"]:
        for failure in report["failed_cases"]:
            lines.append(
                f"- {failure['doc_id']} ({failure['doc_type']}): "
                f"{', '.join(failure['reasons'])}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Review-required Analysis", ""])
    lines.append(f"- Total review-required items: {summary['review_required_count']}")
    lines.extend(["", "## Required Missing Analysis", ""])
    lines.append(f"- Total required missing items: {summary['required_missing_count']}")
    lines.extend(["", "## Badcase Safety", ""])
    lines.append(f"- Badcase violations: {summary['badcase_violation_count']}")
    lines.extend(["", "## Typical Improvements", ""])
    if report["typical_improvements"]:
        for item in report["typical_improvements"]:
            lines.append(f"- {markdown_cell(item)}")
    else:
        lines.append("- See gap analysis for ranked improvement candidates.")
    lines.extend(["", "## Remaining Gaps", ""])
    if report["remaining_gaps"]:
        for gap in report["remaining_gaps"]:
            lines.append(
                f"- {gap['doc_id']} ({gap['doc_type']}): "
                f"missing={gap['required_missing']}; "
                f"review_required={gap['review_required_count']}; "
                f"reasons={gap['failure_reasons']}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Commands",
            "",
            "```powershell",
            "backend\\.venv\\Scripts\\python.exe scripts\\eval_non_procurement_mapping.py "
            "--baseline reports\\non_procurement_baseline_report.json "
            "--out reports\\non_procurement_mapping_eval_report.json "
            "--markdown reports\\non_procurement_mapping_eval_report.md",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _resolve_output(primary: Path | None, alias: Path | None, default: Path) -> Path:
    return primary or alias or default


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--uir-dir", type=Path, default=DEFAULT_UIR_DIR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    rows = non_procurement_rows(load_jsonl(args.gold))
    client = EvaluationHttpClient(
        args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
    )
    items = evaluate_rows(rows, client=client, uir_dir=args.uir_dir)
    report = build_evaluation_report(items, load_baseline(args.baseline))
    attach_run_metadata(report, gold_path=args.gold, dataset_size=len(rows))
    write_json(_resolve_output(args.out, args.out_json, DEFAULT_JSON), report)
    write_markdown(
        _resolve_output(args.markdown, args.out_md, DEFAULT_MD),
        render_markdown(report).splitlines(),
    )


if __name__ == "__main__":
    main()
