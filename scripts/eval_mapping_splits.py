"""Build dev/test/blind mapping summaries from an existing mapping report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from eval_real_world_mapping import build_report, render_markdown  # noqa: E402
from eval_support import safe_ratio, write_json, write_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPLITS = ROOT / "examples" / "real_world" / "splits" / "mapping_split_manifest.json"
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_OUT_DIR = ROOT / "reports" / "mapping_splits"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _split_doc_ids(manifest: dict[str, Any], split: str) -> list[str]:
    entry = manifest.get(split, {})
    if not isinstance(entry, dict):
        return []
    doc_ids = entry.get("doc_ids", [])
    return [doc_id for doc_id in doc_ids if isinstance(doc_id, str)]


def _metric(report: dict[str, Any], key: str) -> float:
    summary = report.get("summary", {})
    value = summary.get(key, 0.0) if isinstance(summary, dict) else 0.0
    return float(value) if isinstance(value, int | float) else 0.0


def _summary_row(
    split: str,
    report: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = report["summary"]
    package_rate = float(summary.get("package_pass_rate", 0.0))
    if "package_pass_rate" not in summary:
        package_rate = safe_ratio(
            int(summary.get("package_pass_count", 0)),
            int(summary.get("document_count", 0)),
        )
    required_missing = sum(
        len(item.get("required_missing", []))
        for item in items
        if isinstance(item.get("required_missing"), list)
    )
    return {
        "split": split,
        "docs": int(summary.get("document_count", 0)),
        "auto_mapping_recall": _metric(report, "auto_mapping_recall"),
        "assisted_mapping_recall": _metric(report, "assisted_mapping_recall")
        or _metric(report, "mapping_recall"),
        "review_required_rate": _metric(report, "review_required_rate"),
        "required_missing": required_missing,
        "missing_gold_mappings": int(summary.get("missing_gold_mappings", 0)),
        "badcase_violations": int(summary.get("badcase_violation_count", 0)),
        "package_pass_rate": package_rate,
    }


def build_split_reports(
    *,
    manifest: dict[str, Any],
    source_report: dict[str, Any],
) -> dict[str, Any]:
    documents = source_report.get("documents") or source_report.get("per_document") or []
    if not isinstance(documents, list):
        raise ValueError("source report must contain documents or per_document list")
    by_id = {
        str(item.get("doc_id")): item
        for item in documents
        if isinstance(item, dict) and item.get("doc_id")
    }
    split_reports: dict[str, dict[str, Any]] = {}
    summary_rows: list[dict[str, Any]] = []
    for split in ("dev", "test", "blind"):
        split_items = [
            _with_candidate_counts(by_id[doc_id])
            for doc_id in _split_doc_ids(manifest, split)
            if doc_id in by_id
        ]
        report = build_report(split_items)
        split_reports[split] = report
        summary_rows.append(_summary_row(split, report, split_items))

    dev = summary_rows[0]
    test = summary_rows[1]
    blind = summary_rows[2]
    dev_test_gap = dev["assisted_mapping_recall"] - test["assisted_mapping_recall"]
    test_blind_gap = test["assisted_mapping_recall"] - blind["assisted_mapping_recall"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "manifest_version": manifest.get("version"),
        "source_report": source_report.get("run_metadata", {}).get("command")
        if isinstance(source_report.get("run_metadata"), dict)
        else None,
        "splits": summary_rows,
        "generalization_gap": {
            "dev_vs_test_assisted_recall": dev_test_gap,
            "test_vs_blind_assisted_recall": test_blind_gap,
            "conclusion": "pass"
            if dev_test_gap <= 0.05
            and test_blind_gap <= 0.05
            and all(row["badcase_violations"] == 0 for row in summary_rows)
            else "review_required",
        },
        "reports": split_reports,
    }


def _with_candidate_counts(item: dict[str, Any]) -> dict[str, Any]:
    copied = dict(item)
    metrics = copied.get("metrics", {})
    if not isinstance(metrics, dict):
        return copied
    metrics = dict(metrics)
    review_count = len(item.get("review_evidence", [])) if isinstance(item.get("review_evidence"), list) else 0
    mapped_count = len(item.get("mapped_or_review_targets", [])) if isinstance(item.get("mapped_or_review_targets"), list) else 0
    metrics.setdefault("review_required_item_count", review_count)
    metrics.setdefault("accepted_item_count", max(mapped_count - review_count, 0))
    copied["metrics"] = metrics
    return copied


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Mapping Split Evaluation Summary",
        "",
        "| Split | Docs | Auto Recall | Assisted Recall | Review Rate | Required Missing | Badcase Violations | Package Pass |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["splits"]:
        lines.append(
            f"| {row['split']} | {row['docs']} | {row['auto_mapping_recall']:.3f} | "
            f"{row['assisted_mapping_recall']:.3f} | {row['review_required_rate']:.3f} | "
            f"{row['required_missing']} | {row['badcase_violations']} | "
            f"{row['package_pass_rate']:.3f} |"
        )
    gap = summary["generalization_gap"]
    lines.extend(
        [
            "",
            "## Generalization Gap",
            "",
            f"- dev vs test assisted recall gap: {gap['dev_vs_test_assisted_recall']:.3f}",
            f"- test vs blind assisted recall gap: {gap['test_vs_blind_assisted_recall']:.3f}",
            f"- conclusion: {gap['conclusion']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    manifest = _load_json(args.splits)
    source_report = _load_json(args.report)
    summary = build_split_reports(manifest=manifest, source_report=source_report)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for split, report in summary["reports"].items():
        write_json(args.out_dir / f"{split}_mapping_eval_report.json", report)
        write_markdown(
            args.out_dir / f"{split}_mapping_eval_report.md",
            render_markdown(report).splitlines(),
        )
    summary_for_json = {key: value for key, value in summary.items() if key != "reports"}
    write_json(args.out_dir / "summary.json", summary_for_json)
    write_markdown(args.out_dir / "summary.md", render_summary(summary).splitlines())


if __name__ == "__main__":
    main()
