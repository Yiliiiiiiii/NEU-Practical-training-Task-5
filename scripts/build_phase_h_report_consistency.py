"""Build a Phase H consistency report with explicit metric definitions."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = ROOT / "reports"
DEFAULT_JSON = ROOT / "reports" / "phase_h_report_consistency.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "phase_h_report_consistency.md"

REPORT_SPECS = {
    "non_procurement_mapping_eval": (
        "phase_h_non_procurement_mapping_eval_report.json",
        "phase_g_non_procurement_mapping_eval_report.json",
        "non_procurement_mapping_eval_report.json",
    ),
    "semantic_mapping_quality": (
        "phase_h_semantic_mapping_quality_report.json",
        "phase_g_semantic_mapping_quality_report.json",
        "semantic_mapping_quality_report.json",
    ),
    "strict_validation_failure_analysis": (
        "phase_h_strict_validation_failure_analysis.json",
        "phase_g_strict_validation_failure_analysis.json",
        "strict_validation_failure_analysis.json",
    ),
}

METRIC_DEFINITIONS = {
    "average_recall": "mean per-document mapping recall over evaluator dataset",
    "strict_pass_count": "number of documents whose strict validation passed",
    "required_missing_doc_count": "number of documents with at least one required missing",
    "required_missing_field_count": "total missing required field incidents",
    "review_required_doc_count": "number of documents with at least one review-required decision",
    "review_required_field_count": "total review-required mapping decisions",
    "badcase_violations": "forbidden mapping accepted count",
    "llm_auto_accepted_count": "LLM-only or LLM-suggested accepted without review count",
    "package_verify_pass_count": "number of generated packages that passed package verification",
}


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("summary", {})
    return value if isinstance(value, dict) else {}


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _first(summary: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in summary:
            return summary[key]
    return None


def _count_docs_with_list(items: list[dict[str, Any]], key: str) -> int | None:
    if not items:
        return None
    saw_key = any(isinstance(item.get(key), list) for item in items)
    if not saw_key:
        return None
    seen = {
        str(item.get("doc_id") or index)
        for index, item in enumerate(items)
        if isinstance(item.get(key), list) and len(item[key]) > 0
    }
    return len(seen)


def _count_list_values(items: list[dict[str, Any]], key: str) -> int | None:
    if not items:
        return None
    saw_key = any(isinstance(item.get(key), list) for item in items)
    if not saw_key:
        return None
    total = sum(len(item.get(key, [])) for item in items if isinstance(item.get(key), list))
    return total


def _review_required_doc_count(report: dict[str, Any]) -> int | None:
    documents = _objects(report.get("documents")) or _objects(report.get("items"))
    if not documents:
        return None
    count = 0
    for item in documents:
        if isinstance(item.get("review_required_count"), int) and item["review_required_count"] > 0:
            count += 1
        elif isinstance(item.get("review_evidence"), list) and item["review_evidence"]:
            count += 1
        elif isinstance(item.get("review_required_fields"), list) and item["review_required_fields"]:
            count += 1
    return count


def _required_missing_doc_count(report: dict[str, Any]) -> int | None:
    documents = _objects(report.get("documents")) or _objects(report.get("items"))
    return _count_docs_with_list(documents, "required_missing")


def _required_missing_field_count(report: dict[str, Any], summary: dict[str, Any]) -> int | None:
    documents = _objects(report.get("documents")) or _objects(report.get("items"))
    counted = _count_list_values(documents, "required_missing")
    if counted is not None:
        return counted
    return _first(summary, "required_missing_field_count", "required_missing_count")


def _review_required_field_count(report: dict[str, Any], summary: dict[str, Any]) -> int | None:
    documents = _objects(report.get("documents")) or _objects(report.get("items"))
    if documents:
        total = 0
        saw = False
        for item in documents:
            if isinstance(item.get("review_required_count"), int):
                total += item["review_required_count"]
                saw = True
            elif isinstance(item.get("review_evidence"), list):
                total += len(item["review_evidence"])
                saw = True
            elif isinstance(item.get("review_required_fields"), list):
                total += len(item["review_required_fields"])
                saw = True
        if saw:
            return total
    return _first(summary, "review_required_field_count", "review_required_count")


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = _summary(report)
    required_missing_doc_count = _required_missing_doc_count(report)
    required_missing_field_count = _required_missing_field_count(report, summary)
    review_required_doc_count = _review_required_doc_count(report)
    review_required_field_count = _review_required_field_count(report, summary)
    return {
        "dataset_size": _first(summary, "dataset_size", "document_count", "package_count"),
        "average_recall": _first(summary, "average_recall", "mapping_recall_average", "mapping_recall"),
        "strict_pass_count": _first(summary, "strict_pass_count", "validation_pass_count"),
        "strict_total": _first(summary, "strict_total", "dataset_size", "package_count", "document_count"),
        "required_missing_doc_count": required_missing_doc_count,
        "required_missing_field_count": required_missing_field_count,
        "review_required_doc_count": review_required_doc_count,
        "review_required_field_count": review_required_field_count,
        "badcase_violations": _first(summary, "badcase_violations", "badcase_violation_count"),
        "llm_auto_accepted_count": _first(summary, "llm_auto_accepted_count"),
        "package_verify_pass_count": _first(summary, "package_verify_pass_count", "package_valid_count"),
    }


def _find_report(reports_root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = reports_root / name
        if path.is_file():
            return path
    return None


def build_report(reports_root: str | Path) -> dict[str, Any]:
    root = Path(reports_root)
    reports: dict[str, dict[str, Any]] = {}
    inputs: dict[str, str | None] = {}
    errors: list[str] = []
    for report_name, candidates in REPORT_SPECS.items():
        path = _find_report(root, candidates)
        inputs[report_name] = str(path) if path else None
        if path is None:
            errors.append(f"missing_report:{report_name}")
            continue
        reports[report_name] = _normalize_report(read_json(path))

    safety_values = [item for item in reports.values()]
    badcase_violations = sum(
        int(item.get("badcase_violations") or 0) for item in safety_values
    )
    llm_auto_accepted_count = sum(
        int(item.get("llm_auto_accepted_count") or 0) for item in safety_values
    )
    if badcase_violations:
        errors.append("badcase_violations_nonzero")
    if llm_auto_accepted_count:
        errors.append("llm_auto_accepted_count_nonzero")

    preferred = reports.get("semantic_mapping_quality") or reports.get("non_procurement_mapping_eval") or {}
    unified_metrics = {
        key: preferred.get(key)
        for key in METRIC_DEFINITIONS
        if key in preferred
    }
    if "badcase_violations" in METRIC_DEFINITIONS:
        unified_metrics["badcase_violations"] = badcase_violations
    if "llm_auto_accepted_count" in METRIC_DEFINITIONS:
        unified_metrics["llm_auto_accepted_count"] = llm_auto_accepted_count

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not errors else "failed",
        "metric_definitions": METRIC_DEFINITIONS,
        "unified_metrics": unified_metrics,
        "reports": reports,
        "safety": {
            "badcase_violations": badcase_violations,
            "llm_auto_accepted_count": llm_auto_accepted_count,
        },
        "inputs": inputs,
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase H Report Consistency",
        "",
        f"- Status: {report['status']}",
        f"- Generated at: {report['generated_at']}",
        "",
        "## Metric Definitions",
        "",
        "| Metric | Definition |",
        "| --- | --- |",
    ]
    for metric, definition in report["metric_definitions"].items():
        lines.append(f"| {metric} | {definition} |")
    lines.extend(
        [
            "",
            "## Reports",
            "",
            "| Report | Dataset | Recall | Strict pass | Required missing docs | Required missing fields | Review docs | Review fields | Badcases | LLM auto accepted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, values in report["reports"].items():
        lines.append(
            f"| {name} | {values.get('dataset_size')} | {values.get('average_recall')} | "
            f"{values.get('strict_pass_count')} | {values.get('required_missing_doc_count')} | "
            f"{values.get('required_missing_field_count')} | {values.get('review_required_doc_count')} | "
            f"{values.get('review_required_field_count')} | {values.get('badcase_violations')} | "
            f"{values.get('llm_auto_accepted_count')} |"
        )
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def run(
    *,
    reports_root: str | Path,
    out_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    report = build_report(reports_root)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORTS_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        reports_root=args.reports_root,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
