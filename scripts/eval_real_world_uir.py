"""Evaluate validated real-world UIR files through the live SchemaPack HTTP API."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from real_world_uir_common import ROOT, markdown_cell, write_json_atomic

SCHEMA_TEMPLATE_MAPPING = {
    "policy_doc": {
        "schema_id": "policy_doc",
        "template_id": "policy_doc_base_v1",
    },
    "procurement_doc": {
        "schema_id": "general_doc",
        "template_id": "general_doc_base_v1",
    },
    "contract_doc": {
        "schema_id": "contract_doc",
        "template_id": "contract_doc_base_v1",
    },
    "meeting_doc": {
        "schema_id": "meeting_doc",
        "template_id": "meeting_doc_base_v1",
    },
    "general_doc": {
        "schema_id": "general_doc",
        "template_id": "general_doc_base_v1",
    },
}


def _json_response(response: httpx.Response) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = response.text[:300]
        raise RuntimeError(f"HTTP {response.status_code}: {detail}") from exc
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("API response must be a JSON object")
    return data


def _high_risk_count(mapping_report: dict[str, Any]) -> int:
    mappings = mapping_report.get("mappings", [])
    if not isinstance(mappings, list):
        return 0
    return sum(
        isinstance(mapping, dict)
        and (
            mapping.get("risk_level") == "high"
            or mapping.get("risk") == "high"
            or (
                isinstance(mapping.get("confidence"), int | float)
                and mapping["confidence"] < 0.5
            )
        )
        for mapping in mappings
    )


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    dataset_size = report["dataset_size"]

    def rate(count: int) -> str:
        return f"{(count / dataset_size * 100):.1f}%" if dataset_size else "0.0%"

    lines = [
        "# Real-world UIR Evaluation Report",
        "",
        f"- Dataset size: {dataset_size}",
        f"- Import success: {report['import_pass_count']} ({rate(report['import_pass_count'])})",
        "- Task execution success: "
        f"{report['task_execute_pass_count']} ({rate(report['task_execute_pass_count'])})",
        "- Package verification success: "
        f"{report['package_verify_pass_count']} "
        f"({rate(report['package_verify_pass_count'])})",
        f"- Mapping review required: {report['mapping_review_required_count']}",
        f"- High-risk mappings: {report['high_risk_mapping_count']}",
        f"- Validation failures: {len(report['validation_failed_cases'])}",
        "",
        "## By document type",
        "",
        "| Document type | Count | Import | Execute | Package | Validation |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for doc_type, metrics in sorted(report["by_doc_type_metrics"].items()):
        lines.append(
            "| {doc_type} | {dataset_size} | {imports} | {executions} | "
            "{packages} | {validations} |".format(
                doc_type=markdown_cell(doc_type),
                dataset_size=metrics["dataset_size"],
                imports=metrics["import_pass_count"],
                executions=metrics["task_execute_pass_count"],
                packages=metrics["package_verify_pass_count"],
                validations=metrics["validation_pass_count"],
            )
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Document | Type | Import | Execute | Package | Error |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["items"]:
        lines.append(
            "| {doc_id} | {doc_type} | {imported} | {executed} | {verified} | {error} |".format(
                doc_id=markdown_cell(item["doc_id"]),
                doc_type=markdown_cell(item["doc_type"]),
                imported="yes" if item["import_passed"] else "no",
                executed="yes" if item["task_execute_passed"] else "no",
                verified="yes" if item["package_verify_passed"] else "no",
                error=markdown_cell(item.get("error", "")),
            )
        )
    lines.extend(
        [
            "",
            "## Typical successes",
            "",
        ]
    )
    lines.extend(f"- {doc_id}" for doc_id in report["typical_success_cases"])
    lines.extend(["", "## Typical failures", ""])
    for item in report["typical_failure_cases"]:
        lines.append(
            f"- {item['doc_id']}: {item['stage']} — "
            f"{item.get('error') or 'downstream validation did not pass'}"
        )
    lines.extend(["", "## Next steps", ""])
    lines.extend(
        f"- {recommendation}"
        for recommendation in report["improvement_recommendations"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_dataset(
    *,
    uir_dir: Path,
    reports_dir: Path,
    packages_dir: Path,
    client: httpx.Client,
) -> dict[str, Any]:
    paths = sorted(
        path for path in uir_dir.glob("*/*.json") if path.parent.name != "_rejected"
    )
    results: list[dict[str, Any]] = []
    for path in paths:
        uir = json.loads(path.read_text(encoding="utf-8"))
        doc_id = str(uir.get("doc_id", path.stem))
        metadata = uir.get("metadata", {})
        doc_type = str(metadata.get("doc_type", metadata.get("domain", "")))
        result: dict[str, Any] = {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "path": path.relative_to(uir_dir).as_posix(),
            "import_passed": False,
            "task_execute_passed": False,
            "package_verify_passed": False,
            "review_required_count": 0,
            "high_risk_mapping_count": 0,
            "validation_passed": False,
        }
        try:
            mapping = SCHEMA_TEMPLATE_MAPPING[doc_type]
            imported = _json_response(
                client.post("/api/v1/documents/import", json={"uir": uir})
            )
            result["import_passed"] = True
            task = _json_response(
                client.post(
                    "/api/v1/tasks",
                    json={
                        "doc_id": imported["doc_id"],
                        "schema_id": mapping["schema_id"],
                        "schema_version": "1.0.0",
                        "template_id": mapping["template_id"],
                        "template_version": "1.0.0",
                        "options": {
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
                        },
                    },
                )
            )
            task_id = str(task["task_id"])
            execution = _json_response(
                client.post(f"/api/v1/tasks/{task_id}/execute")
            )
            result["task_id"] = task_id
            result["task_status"] = execution.get("status")
            result["task_execute_passed"] = execution.get("status") in {
                "completed",
                "review_required",
            }

            reports = {
                name: _json_response(
                    client.get(f"/api/v1/tasks/{task_id}/reports/{route_name}")
                )
                for name, route_name in (
                    ("mapping", "mapping"),
                    ("validation", "validation"),
                    ("content_organization", "content-organization"),
                    ("chunks", "chunks"),
                    ("verifier", "verifier"),
                )
            }
            _json_response(client.get(f"/api/v1/tasks/{task_id}/package"))
            package_response = client.get(f"/api/v1/tasks/{task_id}/package/download")
            package_response.raise_for_status()
            packages_dir.mkdir(parents=True, exist_ok=True)
            package_path = packages_dir / f"{doc_id}.zip"
            package_path.write_bytes(package_response.content)
            result["package_path"] = str(package_path)

            mapping_report = reports["mapping"]
            review_items = mapping_report.get("review_required_items", [])
            result["review_required_count"] = (
                len(review_items) if isinstance(review_items, list) else 0
            )
            result["high_risk_mapping_count"] = _high_risk_count(mapping_report)
            result["validation_passed"] = bool(reports["validation"].get("passed"))
            result["package_verify_passed"] = bool(reports["verifier"].get("passed"))
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"[:500]
        results.append(result)

    by_doc_type = Counter(item["doc_type"] for item in results)
    by_doc_type_metrics: dict[str, dict[str, int]] = {}
    for doc_type in sorted(by_doc_type):
        type_results = [item for item in results if item["doc_type"] == doc_type]
        by_doc_type_metrics[doc_type] = {
            "dataset_size": len(type_results),
            "import_pass_count": sum(item["import_passed"] for item in type_results),
            "task_execute_pass_count": sum(
                item["task_execute_passed"] for item in type_results
            ),
            "package_verify_pass_count": sum(
                item["package_verify_passed"] for item in type_results
            ),
            "validation_pass_count": sum(
                item["validation_passed"] for item in type_results
            ),
        }
    typical_success_cases = [
        item["doc_id"]
        for item in results
        if item["package_verify_passed"] and item["validation_passed"]
    ][:3]
    typical_failure_cases: list[dict[str, str]] = []
    for item in results:
        stage = ""
        if not item["import_passed"]:
            stage = "import"
        elif not item["task_execute_passed"]:
            stage = "task_execute"
        elif not item["package_verify_passed"]:
            stage = "package_verify"
        elif not item["validation_passed"]:
            stage = "validation"
        if stage:
            typical_failure_cases.append(
                {
                    "doc_id": item["doc_id"],
                    "doc_type": item["doc_type"],
                    "stage": stage,
                    "error": str(item.get("error", "")),
                }
            )
        if len(typical_failure_cases) == 3:
            break
    improvement_recommendations = [
        "Review failed cases by stage and add a regression fixture before changing behavior.",
        "Preserve source evidence and human review for ambiguous field mappings.",
        "Add domain aliases only through the existing review and knowledge workflow.",
    ]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_size": len(results),
        "by_doc_type": dict(sorted(by_doc_type.items())),
        "by_doc_type_metrics": by_doc_type_metrics,
        "import_pass_count": sum(item["import_passed"] for item in results),
        "task_execute_pass_count": sum(item["task_execute_passed"] for item in results),
        "package_verify_pass_count": sum(item["package_verify_passed"] for item in results),
        "mapping_review_required_count": sum(
            item["review_required_count"] for item in results
        ),
        "high_risk_mapping_count": sum(
            item["high_risk_mapping_count"] for item in results
        ),
        "validation_failed_cases": [
            item["doc_id"]
            for item in results
            if item["task_execute_passed"] and not item["validation_passed"]
        ],
        "skipped_cases": [
            item["doc_id"] for item in results if not item["import_passed"]
        ],
        "notes": [],
        "typical_success_cases": typical_success_cases,
        "typical_failure_cases": typical_failure_cases,
        "improvement_recommendations": improvement_recommendations,
        "items": results,
    }
    write_json_atomic(reports_dir / "real_world_eval_report.json", report)
    _write_markdown(reports_dir / "real_world_eval_report.md", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uir-dir",
        type=Path,
        default=ROOT / "examples" / "real_world" / "uir",
    )
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=ROOT / "reports" / "real_world_packages",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    with httpx.Client(
        base_url=args.base_url,
        headers=headers,
        timeout=args.timeout,
    ) as client:
        report = evaluate_dataset(
            uir_dir=args.uir_dir,
            reports_dir=args.reports_dir,
            packages_dir=args.packages_dir,
            client=client,
        )
    print(
        {
            "dataset_size": report["dataset_size"],
            "import_pass_count": report["import_pass_count"],
            "task_execute_pass_count": report["task_execute_pass_count"],
            "package_verify_pass_count": report["package_verify_pass_count"],
        }
    )


if __name__ == "__main__":
    main()
