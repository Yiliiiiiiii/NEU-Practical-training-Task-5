"""Analyze validation gaps from existing real-world evaluation artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_support import write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = ROOT / "reports"
DEFAULT_JSON = DEFAULT_REPORTS_DIR / "real_world_validation_gap_analysis.json"
DEFAULT_MD = DEFAULT_REPORTS_DIR / "real_world_validation_gap_analysis.md"
DOC_TYPES = ("general_doc", "meeting_doc", "policy_doc", "procurement_doc")
GENERIC_METADATA_SOURCES = {
    "doc_type",
    "extraction_truncated",
    "retrieved_at",
    "source_format",
    "source_site",
    "source_url",
}
REVIEW_REQUIRED_FIELDS = {
    "announcement_date",
    "award_amount",
    "bid_deadline",
    "budget_amount",
    "created_date",
    "meeting_date",
    "opening_date",
    "publish_date",
}


def _load_json(path: Path, *, required: bool) -> dict[str, Any] | None:
    if not path.is_file():
        if required:
            raise ValueError(f"Required report not found: {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError(f"Report must contain a JSON object: {path}")
    return value


def _objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _first_string(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _target_field(item: dict[str, Any]) -> str | None:
    return _first_string(item, "target_field_id", "target_field", "field_id")


def _source_name(item: dict[str, Any]) -> str | None:
    value = _first_string(item, "source_field_name", "source_name")
    if value:
        return value
    source_field = item.get("source_field")
    if isinstance(source_field, dict):
        return _first_string(source_field, "source_name", "name")
    return None


def _review_items(item: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("review_evidence", "review_required_items"):
        values = _objects(item.get(key))
        if values:
            return values
    mappings = _objects(item.get("mappings"))
    return [
        mapping
        for mapping in mappings
        if mapping.get("status") == "review_required" or mapping.get("need_review")
    ]


def _missing_fields(item: dict[str, Any]) -> list[str]:
    for key in (
        "required_missing",
        "missing_required_fields",
        "unmapped_required_fields",
    ):
        fields = _strings(item.get(key))
        if fields:
            return fields
    unmapped = _objects(item.get("unmapped"))
    return [
        field
        for entry in unmapped
        if entry.get("required")
        and (field := _target_field(entry))
    ]


def _validation_passed(item: dict[str, Any]) -> bool | None:
    for key in ("validation_passed", "strict_pass", "passed", "valid"):
        value = item.get(key)
        if isinstance(value, bool):
            return value
    return None


def _counted(counter: Counter[str], *, limit: int = 5, label: str) -> list[dict[str, Any]]:
    return [
        {label: value, "count": count}
        for value, count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))[
            :limit
        ]
    ]


def _failure_case_by_doc(evaluation_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["doc_id"]): item
        for item in _objects(evaluation_report.get("validation_failed_cases"))
        if item.get("doc_id")
    }


def _document_rows(
    evaluation_report: dict[str, Any],
    mapping_report: dict[str, Any],
    package_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def row_for(doc_id: str) -> dict[str, Any]:
        return rows.setdefault(
            doc_id,
            {
                "doc_id": doc_id,
                "doc_type": None,
                "validation_passed": None,
                "required_missing": [],
                "review_evidence": [],
            },
        )

    for item in _objects(evaluation_report.get("items")):
        doc_id = _first_string(item, "doc_id")
        if not doc_id:
            continue
        row = row_for(doc_id)
        row["doc_type"] = _first_string(item, "doc_type", "schema_id")
        row["validation_passed"] = _validation_passed(item)

    mapping_documents = _objects(mapping_report.get("per_document"))
    if not mapping_documents:
        mapping_documents = _objects(mapping_report.get("items"))
    for item in mapping_documents:
        doc_id = _first_string(item, "doc_id")
        if not doc_id:
            continue
        row = row_for(doc_id)
        row["doc_type"] = _first_string(item, "doc_type", "schema_id") or row["doc_type"]
        passed = _validation_passed(item)
        if passed is not None:
            row["validation_passed"] = passed
        row["required_missing"] = _missing_fields(item)
        row["review_evidence"] = _review_items(item)

    for report in package_reports:
        doc_id = _first_string(report, "doc_id", "_doc_id")
        if not doc_id:
            continue
        row = row_for(doc_id)
        row["doc_type"] = _first_string(report, "doc_type", "schema_id") or row["doc_type"]
        kind = report.get("_report_kind")
        if kind == "validation":
            passed = _validation_passed(report)
            if passed is not None:
                row["validation_passed"] = passed
            missing = _missing_fields(report)
            if missing:
                row["required_missing"] = missing
        elif kind == "mapping":
            reviews = _review_items(report)
            if reviews:
                row["review_evidence"] = reviews

    return [rows[doc_id] for doc_id in sorted(rows)]


def _evidence_text(review: dict[str, Any]) -> list[str]:
    text = _strings(review.get("evidence_text"))
    if text:
        return text
    messages = [
        str(item["message"])
        for item in _objects(review.get("evidence"))
        if item.get("message")
    ]
    reason = _first_string(review, "review_required_reason", "reason")
    return messages or ([reason] if reason else [])


def _is_low_confidence(review: dict[str, Any]) -> bool:
    tier = review.get("confidence_tier")
    confidence = review.get("confidence")
    return tier == "low" or (
        isinstance(confidence, int | float) and not isinstance(confidence, bool)
        and confidence < 0.7
    )


def _recommendations(
    doc_type: str,
    missing: Counter[str],
    review_pairs: Counter[tuple[str, str]],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for (source, target), count in sorted(
        review_pairs.items(),
        key=lambda pair: (-pair[1], pair[0]),
    ):
        if (
            source in GENERIC_METADATA_SOURCES
            or target in REVIEW_REQUIRED_FIELDS
            or target not in missing
            or count < 2
        ):
            continue
        recommendations.append(
            {
                "change_type": "alias",
                "target_field": target,
                "source_alias": source,
                "reason": f"Observed {count} repeated review-required mappings.",
            }
        )
    for field, count in missing.most_common():
        if field not in {"announcement_date", "meeting_date", "publish_date"}:
            continue
        recommendations.append(
            {
                "change_type": "regex",
                "target_field": field,
                "source_pattern": "explicit labeled date with unambiguous YYYY-MM-DD value",
                "reason": (
                    f"{field} is missing in {count} {doc_type} document(s); "
                    "only accept a labeled, single date match."
                ),
            }
        )
    return recommendations[:5]


def analyze_reports(
    evaluation_report: dict[str, Any],
    mapping_report: dict[str, Any],
    *,
    package_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize existing report shapes and aggregate strict validation gaps."""
    rows = _document_rows(evaluation_report, mapping_report, package_reports)
    failed_cases = _failure_case_by_doc(evaluation_report)
    by_type: dict[str, dict[str, Any]] = {}
    field_failures: list[dict[str, Any]] = []
    must_stay_review: dict[tuple[str, str], dict[str, Any]] = {}
    not_recommended: dict[tuple[str, str], dict[str, Any]] = {}

    for doc_type in DOC_TYPES:
        type_rows = [row for row in rows if row.get("doc_type") == doc_type]
        missing_counter: Counter[str] = Counter()
        review_counter: Counter[str] = Counter()
        low_source_counter: Counter[str] = Counter()
        review_pairs: Counter[tuple[str, str]] = Counter()
        for row in type_rows:
            missing_counter.update(row["required_missing"])
            reviews = row["review_evidence"]
            reviews_by_target: dict[str, list[dict[str, Any]]] = {}
            for review in reviews:
                target = _target_field(review)
                source = _source_name(review)
                if target:
                    review_counter[target] += 1
                    reviews_by_target.setdefault(target, []).append(review)
                if source and _is_low_confidence(review):
                    low_source_counter[source] += 1
                if source and target:
                    review_pairs[(source, target)] += 1
                    reason = _first_string(
                        review,
                        "review_required_reason",
                        "reason",
                    ) or "Low-confidence or fuzzy mapping evidence."
                    if target in REVIEW_REQUIRED_FIELDS or "ambiguous" in reason.lower():
                        must_stay_review[(doc_type, target)] = {
                            "doc_type": doc_type,
                            "target_field": target,
                            "reason": reason,
                        }
                    if source in GENERIC_METADATA_SOURCES:
                        not_recommended[(doc_type, target)] = {
                            "doc_type": doc_type,
                            "target_field": target,
                            "reason": (
                                f"Generic metadata source '{source}' is not semantic "
                                "evidence for this target."
                            ),
                        }

            failure_case = failed_cases.get(str(row["doc_id"]), {})
            for field in row["required_missing"]:
                related_reviews = reviews_by_target.get(field, [])
                candidates = sorted(
                    {
                        source
                        for review in related_reviews
                        if (source := _source_name(review))
                    }
                )
                evidence = [
                    text
                    for review in related_reviews
                    for text in _evidence_text(review)
                ]
                fallback_reason = _first_string(failure_case, "error", "reason")
                field_failures.append(
                    {
                        "doc_id": row["doc_id"],
                        "doc_type": doc_type,
                        "target_field": field,
                        "stage": _first_string(failure_case, "stage") or "validation",
                        "reason": fallback_reason or f"Missing required field: {field}",
                        "source_candidates": candidates,
                        "evidence": evidence,
                        "suggested_action": (
                            "Add a narrowly scoped alias or labeled-value extractor "
                            "only after confirming repeated source evidence."
                        ),
                    }
                )
            for field, related_reviews in reviews_by_target.items():
                if field in row["required_missing"]:
                    continue
                candidates = sorted(
                    {
                        source
                        for review in related_reviews
                        if (source := _source_name(review))
                    }
                )
                evidence = [
                    text
                    for review in related_reviews
                    for text in _evidence_text(review)
                ]
                reason = next(
                    (
                        value
                        for review in related_reviews
                        if (
                            value := _first_string(
                                review,
                                "review_required_reason",
                                "reason",
                            )
                        )
                    ),
                    "Mapping confidence or ambiguity requires review.",
                )
                field_failures.append(
                    {
                        "doc_id": row["doc_id"],
                        "doc_type": doc_type,
                        "target_field": field,
                        "stage": "mapping_review",
                        "reason": reason,
                        "source_candidates": candidates,
                        "evidence": evidence,
                        "suggested_action": (
                            "Keep review-required unless repeated labeled evidence "
                            "supports a narrowly scoped template rule."
                        ),
                    }
                )

        strict_pass = sum(row.get("validation_passed") is True for row in type_rows)
        by_type[doc_type] = {
            "doc_count": len(type_rows),
            "strict_pass": strict_pass,
            "strict_failed": len(type_rows) - strict_pass,
            "top_missing_required_fields": _counted(
                missing_counter,
                label="field",
            ),
            "top_review_required_fields": _counted(
                review_counter,
                label="field",
            ),
            "top_low_confidence_sources": _counted(
                low_source_counter,
                label="source",
            ),
            "recommended_template_changes": _recommendations(
                doc_type,
                missing_counter,
                review_pairs,
            ),
        }

    strict_pass_count = sum(row.get("validation_passed") is True for row in rows)
    badcase_violations = _objects(mapping_report.get("badcase_violations"))
    summary = mapping_report.get("summary")
    summary_badcases = (
        summary.get("badcase_violation_count", 0) if isinstance(summary, dict) else 0
    )
    badcase_count = len(badcase_violations) or int(summary_badcases or 0)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "total_docs": len(rows),
            "strict_pass_count": strict_pass_count,
            "strict_failed_count": len(rows) - strict_pass_count,
            "badcase_violation_count": badcase_count,
        },
        "by_doc_type": by_type,
        "field_failures": sorted(
            field_failures,
            key=lambda item: (
                str(item["doc_type"]),
                str(item["doc_id"]),
                str(item["target_field"]),
            ),
        ),
        "fields_that_must_stay_review_required": list(must_stay_review.values()),
        "badcase_warnings": badcase_violations,
        "fields_not_recommended_for_modification": list(not_recommended.values()),
    }


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Real-world Validation Gap Analysis",
        "",
        "## Overview",
        "",
        "| Documents | Strict pass | Strict fail | Badcase violations |",
        "| ---: | ---: | ---: | ---: |",
        (
            f"| {summary['total_docs']} | {summary['strict_pass_count']} | "
            f"{summary['strict_failed_count']} | "
            f"{summary['badcase_violation_count']} |"
        ),
        "",
        "## Strict Pass/Fail by Document Type",
        "",
        "| Document type | Documents | Strict pass | Strict fail |",
        "| --- | ---: | ---: | ---: |",
    ]
    for doc_type, metrics in report["by_doc_type"].items():
        lines.append(
            f"| {doc_type} | {metrics['doc_count']} | {metrics['strict_pass']} | "
            f"{metrics['strict_failed']} |"
        )

    lines.extend(["", "## Top Failed and Review-required Fields", ""])
    for doc_type, metrics in report["by_doc_type"].items():
        missing = ", ".join(
            f"{item['field']} ({item['count']})"
            for item in metrics["top_missing_required_fields"]
        ) or "None"
        reviews = ", ".join(
            f"{item['field']} ({item['count']})"
            for item in metrics["top_review_required_fields"]
        ) or "None"
        lines.append(f"- {doc_type}: failed={missing}; review-required={reviews}")

    lines.extend(["", "## Recommended Aliases and Regexes", ""])
    recommendations = [
        (doc_type, recommendation)
        for doc_type, metrics in report["by_doc_type"].items()
        for recommendation in metrics["recommended_template_changes"]
    ]
    if recommendations:
        for doc_type, item in recommendations:
            source = item.get("source_alias") or item.get("source_pattern")
            lines.append(
                f"- {doc_type}.{item['target_field']}: {item['change_type']} "
                f"`{_markdown_cell(source)}` — {_markdown_cell(item['reason'])}"
            )
    else:
        lines.append("- None. Current evidence does not justify an automatic template change.")

    lines.extend(["", "## Fields That Must Stay Review-required", ""])
    if report["fields_that_must_stay_review_required"]:
        for item in report["fields_that_must_stay_review_required"]:
            lines.append(
                f"- {item['doc_type']}.{item['target_field']}: "
                f"{_markdown_cell(item['reason'])}"
            )
    else:
        lines.append("- None identified.")

    lines.extend(["", "## Badcase Warnings", ""])
    if report["badcase_warnings"]:
        for item in report["badcase_warnings"]:
            lines.append(
                f"- {item.get('doc_id', 'unknown')}: "
                f"{item.get('case_id', item.get('reason', 'badcase violation'))}"
            )
    else:
        lines.append("- No violations detected; retain the existing badcase guards.")

    lines.extend(["", "## Fields Not Recommended for Modification", ""])
    if report["fields_not_recommended_for_modification"]:
        for item in report["fields_not_recommended_for_modification"]:
            lines.append(
                f"- {item['doc_type']}.{item['target_field']}: "
                f"{_markdown_cell(item['reason'])}"
            )
    else:
        lines.append("- None identified.")
    return "\n".join(lines) + "\n"


def discover_package_reports(reports_dir: Path) -> list[dict[str, Any]]:
    package_root = reports_dir / "real_world_packages"
    if not package_root.is_dir():
        return []
    reports: list[dict[str, Any]] = []
    for filename, kind in (
        ("validation_report.json", "validation"),
        ("mapping_report.json", "mapping"),
    ):
        for path in sorted(package_root.rglob(filename)):
            payload = _load_json(path, required=False)
            if payload is None:
                continue
            payload["_report_kind"] = kind
            payload.setdefault("_doc_id", path.parent.name)
            reports.append(payload)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--evaluation-report", type=Path)
    parser.add_argument("--mapping-report", type=Path)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    evaluation_path = (
        args.evaluation_report or args.reports_dir / "real_world_eval_report.json"
    )
    mapping_path = (
        args.mapping_report or args.reports_dir / "real_world_mapping_eval_report.json"
    )
    try:
        evaluation_report = _load_json(evaluation_path, required=True)
        mapping_report = _load_json(mapping_path, required=True)
        assert evaluation_report is not None
        assert mapping_report is not None
        report = analyze_reports(
            evaluation_report,
            mapping_report,
            package_reports=discover_package_reports(args.reports_dir),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
