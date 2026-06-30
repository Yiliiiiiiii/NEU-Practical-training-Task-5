"""Evaluate real-world mapping quality against source-backed gold labels."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from eval_support import (
    EvaluationHttpClient,
    aggregate_mapping_metrics,
    load_jsonl,
    safe_ratio,
    score_mapping_report,
    write_json,
    write_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "real_world_mapping_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "real_world_mapping_eval_report.md"
DEFAULT_UIR_SOURCE_PREFIX = "examples/real_world/uir/"


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _mapping_options() -> dict[str, Any]:
    return {
        "enable_llm_fallback": False,
        "content_organization": {
            "chunk_strategy": "heading_aware",
            "target_tokens": 768,
            "min_tokens": 128,
            "max_tokens": 1024,
            "overlap_tokens": 80,
            "protect_tables": True,
            "protect_lists": True,
            "protect_code_blocks": True,
            "enable_parent_child": False,
            "enable_light_semantic_boundary": True,
            "summary_mode": "deterministic",
            "keyword_mode": "deterministic",
        },
    }


def resolve_uir_path(gold: dict[str, Any], uir_dir: Path) -> Path:
    source_path = str(gold["source_path"])
    if source_path.startswith(DEFAULT_UIR_SOURCE_PREFIX):
        return uir_dir / source_path.removeprefix(DEFAULT_UIR_SOURCE_PREFIX)
    path = Path(source_path)
    if path.is_absolute():
        return path
    return ROOT / path


def mapped_or_review_targets(mapping_report: dict[str, Any]) -> set[str]:
    targets: set[str] = set()
    for key in ("mappings", "review_required_items"):
        items = mapping_report.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            target = item.get("target_field_id") or item.get("target_field")
            if isinstance(target, str) and target:
                targets.add(target)
            candidates = item.get("target_field_candidates")
            if isinstance(candidates, list):
                targets.update(
                    candidate for candidate in candidates if isinstance(candidate, str)
                )
    return targets


def _is_fatal_http_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        httpx.InvalidURL
        | httpx.TransportError
        | httpx.TimeoutException
        | httpx.UnsupportedProtocol,
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {401, 403}
    return False


def execute_gold_row(
    gold: dict[str, Any],
    *,
    client: EvaluationHttpClient,
    uir_dir: Path = DEFAULT_UIR_DIR,
    schema_id: str | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    uir_path = resolve_uir_path(gold, uir_dir)
    uir = json.loads(uir_path.read_text(encoding="utf-8"))
    item: dict[str, Any] = {
        "doc_id": gold["doc_id"],
        "doc_type": gold["doc_type"],
        "schema_id": schema_id or gold["schema_id"],
        "template_id": template_id or gold["template_id"],
        "package_passed": False,
        "validation_passed": False,
        "review_evidence": [],
        "required_missing": [],
    }
    try:
        imported = client.import_document(uir)
        task = client.create_task(
            {
                "doc_id": imported["doc_id"],
                "schema_id": item["schema_id"],
                "schema_version": "1.0.0",
                "template_id": item["template_id"],
                "template_version": "1.0.0",
                "options": _mapping_options(),
            }
        )
        task_id = str(task["task_id"])
        execution = client.execute_task(task_id)
        item["task_id"] = task_id
        item["task_status"] = execution.get("status")
        mapping_report = client.report(task_id, "mapping")
        validation_report = client.report(task_id, "validation")
        verifier_report = client.report(task_id, "verifier")
        client.package(task_id)

        item["metrics"] = score_mapping_report(gold, mapping_report)
        item["validation_passed"] = bool(validation_report.get("passed"))
        item["package_passed"] = bool(verifier_report.get("passed"))
        item["mapped_or_review_targets"] = sorted(mapped_or_review_targets(mapping_report))
        review_items = mapping_report.get("review_required_items", [])
        item["review_evidence"] = review_items if isinstance(review_items, list) else []
        unmapped = mapping_report.get("unmapped", [])
        if isinstance(unmapped, list):
            item["required_missing"] = [
                field.get("target_field_id") or field.get("field_id")
                for field in unmapped
                if isinstance(field, dict)
                and field.get("required")
                and (field.get("target_field_id") or field.get("field_id"))
            ]
    except Exception as exc:
        if _is_fatal_http_error(exc):
            raise
        item["error"] = f"{type(exc).__name__}: {exc}"[:500]
        item["metrics"] = score_mapping_report(gold, {})
    return item


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    client: EvaluationHttpClient,
    uir_dir: Path = DEFAULT_UIR_DIR,
    schema_id: str | None = None,
    template_id: str | None = None,
) -> list[dict[str, Any]]:
    return [
        execute_gold_row(
            row,
            client=client,
            uir_dir=uir_dir,
            schema_id=schema_id,
            template_id=template_id,
        )
        for row in rows
    ]


def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    metrics_rows = [item.get("metrics", {}) for item in items]
    metrics = aggregate_mapping_metrics(metrics_rows)
    package_pass_count = sum(1 for item in items if item.get("package_passed"))
    validation_pass_count = sum(1 for item in items if item.get("validation_passed"))
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_type[str(item.get("doc_type", "unknown"))].append(item)

    per_doc_type: dict[str, dict[str, Any]] = {}
    for doc_type, type_items in sorted(by_type.items()):
        type_metrics = aggregate_mapping_metrics(
            [item.get("metrics", {}) for item in type_items]
        )
        per_doc_type[doc_type] = {
            **type_metrics,
            "package_pass_rate": safe_ratio(
                sum(1 for item in type_items if item.get("package_passed")),
                len(type_items),
            ),
        }

    badcase_violations = [
        {
            "doc_id": item.get("doc_id"),
            **violation,
        }
        for item in items
        for violation in item.get("metrics", {}).get("badcase_violations", [])
    ]
    per_field: dict[str, dict[str, int]] = defaultdict(
        lambda: {"missing_gold_mappings": 0, "badcase_violation_count": 0}
    )
    for item in items:
        for violation in item.get("metrics", {}).get("badcase_violations", []):
            target = str(violation.get("target_field", "unknown"))
            per_field[target]["badcase_violation_count"] += 1
        for field_id in item.get("required_missing", []):
            per_field[str(field_id)]["missing_gold_mappings"] += 1

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            **metrics,
            "package_pass_count": package_pass_count,
            "package_pass_rate": safe_ratio(package_pass_count, len(items)),
            "validation_pass_count": validation_pass_count,
        },
        "per_document_type": per_doc_type,
        "per_document": items,
        "per_field": dict(sorted(per_field.items())),
        "missing_or_ambiguous": [
            {
                "doc_id": item.get("doc_id"),
                "required_missing": item.get("required_missing", []),
                "review_evidence_count": len(item.get("review_evidence", [])),
            }
            for item in items
            if item.get("required_missing") or item.get("review_evidence")
        ],
        "badcase_violations": badcase_violations,
        "review_evidence": [
            {"doc_id": item.get("doc_id"), "items": item.get("review_evidence", [])}
            for item in items
            if item.get("review_evidence")
        ],
        "package_summary": {
            "passed": package_pass_count,
            "failed": len(items) - package_pass_count,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Real-world Mapping Evaluation",
        "",
        "## Summary",
        "",
        f"- Documents: {summary['document_count']}",
        f"- Mapping recall: {summary['mapping_recall']:.3f}",
        f"- Package pass rate: {summary['package_pass_rate']:.3f}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        "",
        "## Per Document Type",
        "",
        "| Document type | Documents | Mapping recall | Package pass rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    for doc_type, metrics in report["per_document_type"].items():
        lines.append(
            f"| {markdown_cell(doc_type)} | {metrics['document_count']} | "
            f"{metrics['mapping_recall']:.3f} | {metrics['package_pass_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Per Field",
            "",
            "| Field | Missing required | Badcase violations |",
            "| --- | ---: | ---: |",
        ]
    )
    for field, metrics in report["per_field"].items():
        lines.append(
            f"| {markdown_cell(field)} | {metrics['missing_gold_mappings']} | "
            f"{metrics['badcase_violation_count']} |"
        )
    lines.extend(["", "## Missing Or Ambiguous", ""])
    if report["missing_or_ambiguous"]:
        for item in report["missing_or_ambiguous"]:
            lines.append(
                f"- {item['doc_id']}: missing={item['required_missing']}, "
                f"review_evidence={item['review_evidence_count']}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Badcase Violations", ""])
    if report["badcase_violations"]:
        for item in report["badcase_violations"]:
            lines.append(
                f"- {item.get('doc_id')}: {item.get('case_id')} -> "
                f"{item.get('target_field')}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Review Evidence", ""])
    if report["review_evidence"]:
        for item in report["review_evidence"]:
            lines.append(f"- {item['doc_id']}: {len(item['items'])} item(s)")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Package Verification Summary",
            "",
            f"- Passed: {report['package_summary']['passed']}",
            f"- Failed: {report['package_summary']['failed']}",
        ]
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

    rows = load_jsonl(args.gold)
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
