"""Compare procurement-specific catalog coverage against generic document mapping."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from eval_real_world_mapping import build_report as build_mapping_report
from eval_real_world_mapping import evaluate_rows
from eval_real_world_mapping import render_markdown as render_mapping_markdown
from eval_support import EvaluationHttpClient, load_jsonl, safe_ratio, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "procurement_doc_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "procurement_doc_eval_report.md"
GENERAL = ("general_doc", "general_doc_base_v1")
PROCUREMENT = ("procurement_doc", "procurement_doc_base_v1")
REQUIRED_FIELDS = {"title", "project_name", "purchaser"}


def _side_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    report = build_mapping_report(items)
    summary = report["summary"]
    missing_required = sum(len(item.get("required_missing", [])) for item in items)
    required_total = len(items) * len(REQUIRED_FIELDS)
    return {
        "document_count": summary["document_count"],
        "gold_recall": summary["mapping_recall"],
        "required_coverage": safe_ratio(required_total - missing_required, required_total),
        "missing_required_count": missing_required,
        "badcase_violation_count": summary["badcase_violation_count"],
        "package_pass_rate": summary["package_pass_rate"],
        "raw_report": report,
    }


def apply_procurement_required_coverage(items: list[dict[str, Any]]) -> None:
    for item in items:
        targets = {
            target
            for target in item.get("mapped_or_review_targets", [])
            if isinstance(target, str)
        }
        item["required_missing"] = sorted(REQUIRED_FIELDS - targets)


def build_report(
    *,
    general_items: list[dict[str, Any]],
    procurement_items: list[dict[str, Any]],
) -> dict[str, Any]:
    general = _side_summary(general_items)
    procurement = _side_summary(procurement_items)
    return {
        "general_doc": general,
        "procurement_doc": procurement,
        "delta": {
            "label": "procurement_doc - general_doc",
            "mapping_recall": procurement["gold_recall"] - general["gold_recall"],
            "required_coverage": (
                procurement["required_coverage"] - general["required_coverage"]
            ),
            "badcase_violation_count": (
                procurement["badcase_violation_count"]
                - general["badcase_violation_count"]
            ),
            "package_pass_rate": (
                procurement["package_pass_rate"] - general["package_pass_rate"]
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Procurement Catalog Evaluation",
        "",
        "## Summary",
        "",
        f"- Delta: {report['delta']['label']}",
        f"- Gold recall delta: {report['delta']['mapping_recall']:.3f}",
        f"- Required coverage delta: {report['delta']['required_coverage']:.3f}",
        "",
        "## Required Coverage",
        "",
        "| Catalog | Required coverage | Missing required |",
        "| --- | ---: | ---: |",
    ]
    for key in ("general_doc", "procurement_doc"):
        side = report[key]
        lines.append(
            f"| {key} | {side['required_coverage']:.3f} | "
            f"{side['missing_required_count']} |"
        )
    lines.extend(
        [
            "",
            "## Gold Recall Delta",
            "",
            "| Catalog | Gold recall | Package pass rate |",
            "| --- | ---: | ---: |",
        ]
    )
    for key in ("general_doc", "procurement_doc"):
        side = report[key]
        lines.append(
            f"| {key} | {side['gold_recall']:.3f} | "
            f"{side['package_pass_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Badcase Comparison",
            "",
            "| Catalog | Badcase violations |",
            "| --- | ---: |",
        ]
    )
    for key in ("general_doc", "procurement_doc"):
        lines.append(f"| {key} | {report[key]['badcase_violation_count']} |")
    lines.extend(
        [
            "",
            "## Procurement Detail",
            "",
            render_mapping_markdown(report["procurement_doc"]["raw_report"]),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _procurement_rows(gold_path: Path) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(gold_path) if row.get("doc_type") == "procurement_doc"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--uir-dir", type=Path, default=DEFAULT_UIR_DIR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    rows = _procurement_rows(args.gold)
    client = EvaluationHttpClient(
        args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
    )
    general_items = evaluate_rows(
        rows,
        client=client,
        uir_dir=args.uir_dir,
        schema_id=GENERAL[0],
        template_id=GENERAL[1],
    )
    procurement_items = evaluate_rows(
        rows,
        client=client,
        uir_dir=args.uir_dir,
        schema_id=PROCUREMENT[0],
        template_id=PROCUREMENT[1],
    )
    apply_procurement_required_coverage(general_items)
    apply_procurement_required_coverage(procurement_items)
    report = build_report(
        general_items=general_items,
        procurement_items=procurement_items,
    )
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
