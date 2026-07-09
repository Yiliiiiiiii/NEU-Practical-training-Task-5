"""Write a reproducible baseline snapshot for mapping metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_OUT = ROOT / "reports" / "mapping_metric_baseline_snapshot.md"
DEFAULT_COMMAND = (
    "backend\\.venv\\Scripts\\python.exe scripts\\eval_non_procurement_mapping.py "
    "--baseline reports\\non_procurement_baseline_report.json "
    "--out reports\\non_procurement_mapping_eval_report.json "
    "--markdown reports\\non_procurement_mapping_eval_report.md"
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        return {}
    computed = dict(summary)
    if "auto_mapping_recall" in computed and "assisted_mapping_recall" in computed:
        return computed
    documents = report.get("documents") or report.get("per_document") or []
    if not isinstance(documents, list):
        return computed
    gold_signal_count = 0
    auto_correct = 0
    review_correct = 0
    review_items = 0
    accepted_items = 0
    missing_gold = 0
    gold_mapping_count = 0
    for item in documents:
        if not isinstance(item, dict):
            continue
        metrics = item.get("metrics", {})
        if not isinstance(metrics, dict):
            continue
        gold_signals = metrics.get("gold_signal_count")
        if not isinstance(gold_signals, int | float):
            gold_signals = int(metrics.get("gold_mapping_count", 0)) + int(
                metrics.get("gold_review_required_count", 0)
            )
        gold_signal_count += int(gold_signals)
        gold_mapping_count += int(metrics.get("gold_mapping_count", 0))
        auto_correct += int(metrics.get("auto_accepted_correct", 0))
        review_correct += int(metrics.get("review_required_correct", 0))
        missing_gold += int(metrics.get("missing_gold_mappings", 0))
        reviews = item.get("review_evidence", [])
        review_count = len(reviews) if isinstance(reviews, list) else 0
        mapped = item.get("mapped_or_review_targets", [])
        mapped_count = len(mapped) if isinstance(mapped, list) else 0
        review_items += int(metrics.get("review_required_item_count", review_count))
        accepted_items += int(
            metrics.get("accepted_item_count", max(mapped_count - review_count, 0))
        )
    if gold_signal_count:
        computed["auto_mapping_recall"] = auto_correct / gold_signal_count
        computed["assisted_mapping_recall"] = (
            auto_correct + review_correct
        ) / gold_signal_count
        computed["review_required_recall"] = review_correct / gold_signal_count
    if accepted_items + review_items:
        computed["review_required_rate"] = review_items / (accepted_items + review_items)
    if gold_mapping_count:
        computed["missing_gold_mapping_rate"] = missing_gold / gold_mapping_count
    computed["missing_gold_mappings"] = missing_gold
    return computed


def render_snapshot(report: dict[str, Any], *, command: str) -> str:
    summary = _summary(report)
    assisted = summary.get("assisted_mapping_recall", summary.get("average_recall", 0.0))
    lines = [
        "# Mapping Metric Baseline Snapshot",
        "",
        "## Reproducible Command",
        "",
        "```powershell",
        command,
        "```",
        "",
        "## Current Metrics",
        "",
        f"- dataset_size: {summary.get('dataset_size', summary.get('document_count', 0))}",
        f"- average_recall: {summary.get('average_recall', summary.get('mapping_recall', 0.0))}",
        f"- auto_mapping_recall: {summary.get('auto_mapping_recall', 0.0)}",
        f"- assisted_mapping_recall: {assisted}",
        f"- review_required_rate: {summary.get('review_required_rate', 0.0)}",
        f"- review_required_count: {summary.get('review_required_count', 0)}",
        f"- required_missing_count: {summary.get('required_missing_count', 0)}",
        f"- badcase_violations: {summary.get('badcase_violation_count', 0)}",
        f"- package_verification_pass: {summary.get('package_verify_pass_count', summary.get('package_pass_count', 0))}",
        "",
        "## Metric Definition",
        "",
        "- auto_mapping_recall counts only automatically accepted correct mappings.",
        "- assisted_mapping_recall counts automatically accepted correct mappings plus review-required correct candidates.",
        "- legacy mapping_recall/average_recall is retained as assisted mapping recall for historical compatibility.",
        "- review_required_rate reports the share of mapping outputs that require human review.",
        "",
        "## Known Inconsistencies",
        "",
        "- Historical README and Phase D/Phase I reports used `average recall` or `mapping_recall` without always naming the assisted-recall denominator.",
        "- This snapshot is the baseline for the 0.85 sprint; older reports should be treated as historical.",
        "",
        "## Decision",
        "",
        "Use this report as the baseline for the 0.85 improvement sprint.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--command", default=DEFAULT_COMMAND)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_snapshot(_load_json(args.report), command=args.command),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
