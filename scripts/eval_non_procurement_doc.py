"""Evaluate real non-procurement UIR documents against their specific catalogs."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_real_world_mapping import evaluate_rows
from eval_support import EvaluationHttpClient, load_jsonl, safe_ratio, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "non_procurement_doc_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "non_procurement_doc_eval_report.md"

CATALOGS = {
    "general_doc": ("general_doc", "general_doc_base_v1"),
    "meeting_doc": ("meeting_doc", "meeting_doc_base_v1"),
    "policy_doc": ("policy_doc", "policy_doc_base_v1"),
}
THRESHOLDS = {
    "general_doc": 2,
    "meeting_doc": 2,
    "policy_doc": 3,
    "mapping_recall": 0.65,
}


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def non_procurement_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        doc_type = row.get("doc_type")
        if not isinstance(doc_type, str) or doc_type not in CATALOGS:
            continue
        schema_id, template_id = CATALOGS[doc_type]
        selected.append({**row, "schema_id": schema_id, "template_id": template_id})
    return selected


def _metric(item: dict[str, Any], key: str, default: int | float = 0) -> int | float:
    metrics = item.get("metrics", {})
    if not isinstance(metrics, dict):
        return default
    value = metrics.get(key, default)
    return value if isinstance(value, int | float) else default


def _list(item: dict[str, Any], key: str) -> list[Any]:
    value = item.get(key, [])
    return value if isinstance(value, list) else []


def _error_messages(item: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    errors = item.get("errors", [])
    if isinstance(errors, list):
        messages.extend(str(error) for error in errors if error)
    error = item.get("error")
    if error:
        messages.append(str(error))
    return messages


def _mapped_or_review_count(item: dict[str, Any]) -> int:
    targets = item.get("mapped_or_review_targets", [])
    if isinstance(targets, list):
        return len({target for target in targets if isinstance(target, str) and target})
    metrics = item.get("metrics", {})
    if not isinstance(metrics, dict):
        return 0
    accepted = metrics.get("auto_accepted_correct", 0)
    reviewed = metrics.get("review_required_correct", 0)
    if isinstance(accepted, int | float) and isinstance(reviewed, int | float):
        return int(accepted + reviewed)
    return 0


def _strict_passed(item: dict[str, Any]) -> bool:
    explicit = item.get("strict_passed")
    doc_type = str(item.get("doc_type", ""))
    required_target_threshold = THRESHOLDS.get(doc_type, 0)
    facts_passed = (
        not _error_messages(item)
        and _metric(item, "mapping_recall") >= THRESHOLDS["mapping_recall"]
        and len(_list(item, "required_missing")) == 0
        and len(_list(item, "high_risk_auto_accepted")) == 0
        and _metric(item, "badcase_violation_count") == 0
        and _mapped_or_review_count(item) >= required_target_threshold
        and item.get("package_passed", True) is True
    )
    if isinstance(explicit, bool):
        return explicit and facts_passed
    return facts_passed


def _failure_reasons(item: dict[str, Any], strict_passed: bool) -> list[str]:
    reasons: list[str] = []
    if not strict_passed:
        reasons.append("strict_pass_failed")
    if _error_messages(item):
        reasons.append("evaluation_error")
    if len(_list(item, "required_missing")) > 0:
        reasons.append("missing_required_fields")
    if _metric(item, "mapping_recall") < THRESHOLDS["mapping_recall"]:
        reasons.append("mapping_recall_below_threshold")
    if len(_list(item, "high_risk_auto_accepted")) > 0:
        reasons.append("high_risk_auto_accepted")
    if _metric(item, "badcase_violation_count") > 0:
        reasons.append("badcase_violation")
    if _mapped_or_review_count(item) < THRESHOLDS.get(str(item.get("doc_type", "")), 0):
        reasons.append("mapped_or_review_targets_below_threshold")
    if item.get("package_passed") is False:
        reasons.append("package_invalid")
    return reasons


def _aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    document_count = len(items)
    strict_pass_count = sum(1 for item in items if _strict_passed(item))
    required_missing_count = sum(len(_list(item, "required_missing")) for item in items)
    review_required_count = sum(len(_list(item, "review_evidence")) for item in items)
    high_risk_auto_accepted_count = sum(
        len(_list(item, "high_risk_auto_accepted")) for item in items
    )
    badcase_violation_count = sum(
        int(_metric(item, "badcase_violation_count")) for item in items
    )
    package_items = [item for item in items if "package_passed" in item]
    package_valid_count = sum(1 for item in package_items if item.get("package_passed"))
    mapping_recall_total = sum(float(_metric(item, "mapping_recall")) for item in items)
    return {
        "document_count": document_count,
        "strict_pass_count": strict_pass_count,
        "strict_pass_rate": safe_ratio(strict_pass_count, document_count),
        "required_missing_count": required_missing_count,
        "mapping_recall_average": safe_ratio(mapping_recall_total, document_count),
        "review_required_count": review_required_count,
        "high_risk_auto_accepted_count": high_risk_auto_accepted_count,
        "badcase_violation_count": badcase_violation_count,
        "package_valid_count": package_valid_count,
        "package_valid_rate": safe_ratio(package_valid_count, len(package_items)),
    }


def _document(item: dict[str, Any]) -> dict[str, Any]:
    doc_type = str(item.get("doc_type", "unknown"))
    strict_passed = _strict_passed(item)
    return {
        **item,
        "catalog": {
            "schema_id": item.get("schema_id", CATALOGS.get(doc_type, ("", ""))[0]),
            "template_id": item.get("template_id", CATALOGS.get(doc_type, ("", ""))[1]),
        },
        "required_missing": _list(item, "required_missing"),
        "review_evidence": _list(item, "review_evidence"),
        "high_risk_auto_accepted": _list(item, "high_risk_auto_accepted"),
        "strict_passed": strict_passed,
        "failure_reasons": _failure_reasons(item, strict_passed),
    }


def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    documents = [_document(item) for item in items]
    by_doc_type = {
        doc_type: _aggregate([item for item in documents if item.get("doc_type") == doc_type])
        for doc_type in CATALOGS
    }
    failures = [
        {
            "doc_id": item.get("doc_id"),
            "doc_type": item.get("doc_type"),
            "reasons": item["failure_reasons"],
        }
        for item in documents
        if item["failure_reasons"]
    ]
    errors = [
        {
            "doc_id": item.get("doc_id"),
            "doc_type": item.get("doc_type"),
            "message": message,
        }
        for item in documents
        for message in _error_messages(item)
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "thresholds": THRESHOLDS,
        "catalogs": {
            key: {"schema_id": schema_id, "template_id": template_id}
            for key, (schema_id, template_id) in CATALOGS.items()
        },
        "summary": _aggregate(documents),
        "by_doc_type": by_doc_type,
        "documents": documents,
        "failures": failures,
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Non-procurement Document Evaluation",
        "",
        "## Summary",
        "",
        f"- Documents: {summary['document_count']}",
        f"- Strict pass rate: {summary['strict_pass_rate']:.3f}",
        f"- Mapping recall average: {summary['mapping_recall_average']:.3f}",
        f"- Required missing: {summary['required_missing_count']}",
        f"- Review required: {summary['review_required_count']}",
        f"- High-risk auto accepted: {summary['high_risk_auto_accepted_count']}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        f"- Package valid: {summary['package_valid_count']}",
        "",
        "## Thresholds",
        "",
        f"- Mapping recall: {report['thresholds']['mapping_recall']:.2f}",
        f"- General document minimum mapped/review targets: {report['thresholds']['general_doc']}",
        f"- Meeting document minimum mapped/review targets: {report['thresholds']['meeting_doc']}",
        f"- Policy document minimum mapped/review targets: {report['thresholds']['policy_doc']}",
        "",
        "## By Document Type",
        "",
        "| Type | Documents | Strict pass | Recall avg | Missing required | Package valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for doc_type, metrics in report["by_doc_type"].items():
        lines.append(
            f"| {markdown_cell(doc_type)} | {metrics['document_count']} | "
            f"{metrics['strict_pass_count']} | "
            f"{metrics['mapping_recall_average']:.3f} | "
            f"{metrics['required_missing_count']} | "
            f"{metrics['package_valid_count']} |"
        )
    lines.extend(["", "## Failures", ""])
    if report["failures"]:
        for failure in report["failures"]:
            lines.append(
                f"- {failure['doc_id']} ({failure['doc_type']}): "
                f"{', '.join(failure['reasons'])}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Errors", ""])
    if report["errors"]:
        for error in report["errors"]:
            lines.append(
                f"- {error['doc_id']} ({error['doc_type']}): {markdown_cell(error['message'])}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Documents",
            "",
            "| Document | Type | Strict pass | Recall | Missing required | Review required | Package valid |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in report["documents"]:
        lines.append(
            f"| {markdown_cell(item.get('doc_id'))} | {markdown_cell(item.get('doc_type'))} | "
            f"{1 if item.get('strict_passed') else 0} | "
            f"{float(_metric(item, 'mapping_recall')):.3f} | "
            f"{len(_list(item, 'required_missing'))} | "
            f"{len(_list(item, 'review_evidence'))} | "
            f"{1 if item.get('package_passed') else 0} |"
        )
    return "\n".join(lines) + "\n"


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

    rows = non_procurement_rows(load_jsonl(args.gold))
    client = EvaluationHttpClient(
        args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
    )
    report = build_report(evaluate_rows(rows, client=client, uir_dir=args.uir_dir))
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
