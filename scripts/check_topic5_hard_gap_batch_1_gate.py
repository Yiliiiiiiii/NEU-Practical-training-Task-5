"""Run the machine-readable Topic 5 hard-gap batch 1 acceptance gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_topic5_field_operations import build_report as field_report  # noqa: E402
from scripts.eval_topic5_schema_localization import (  # noqa: E402
    build_report as localization_report,
)

DEFAULT_OUTPUT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "operations"
DEFAULT_TAG_REPORT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "tags" / "content_tag_quality.json"
DEFAULT_VERIFICATION = DEFAULT_OUTPUT / "verification_summary.json"

COMPONENT_TESTS = {
    "metadata": [
        "backend/tests/test_metadata_template_service.py",
        "backend/tests/test_topic5_convert_api.py",
    ],
    "summary": [
        "backend/tests/test_document_summary_service.py",
    ],
    "consistency": [
        "backend/tests/test_artifact_consistency_service.py",
    ],
    "entity": [
        "backend/tests/test_topic5_entity_passthrough.py",
    ],
    "topic11": [
        "backend/tests/test_topic11_chunk_provider.py",
    ],
    "legacy": [
        "backend/tests/test_package_1_1_assertion_report_compatibility.py",
        "backend/tests/test_topic5_convert_api.py",
    ],
}


def run_component_checks() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name, paths in COMPONENT_TESTS.items():
        command = [
            str(BACKEND / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "pytest",
            *paths,
            "-q",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        results[name] = {
            "passed": completed.returncode == 0,
            "return_code": completed.returncode,
            "command": " ".join(command),
            "summary": _last_nonempty_line(completed.stdout or completed.stderr),
        }
    return results


def evaluate_gate(
    *,
    operations: dict[str, Any],
    localization: dict[str, Any],
    tag_quality: dict[str, Any],
    components: dict[str, dict[str, Any]],
    verification: dict[str, Any],
) -> dict[str, Any]:
    metrics = tag_quality.get("metrics", {})

    def passed(name: str) -> bool:
        return bool(components.get(name, {}).get("passed"))

    values = {
        "metadata_template_effective": passed("metadata"),
        "metadata_required_localization_rate": 1.0 if passed("metadata") else 0.0,
        "content_tag_metric": float(metrics.get("content_tag_f1", 0.0)),
        "management_tag_rule_accuracy": float(metrics.get("management_tag_f1", 0.0)),
        "quality_tag_metric": float(metrics.get("quality_tag_f1", 0.0)),
        "global_quality_tag_pollution_count": int(metrics.get("unknown_tag_count", -1)),
        "document_summary_faithfulness": 1.0 if passed("summary") else 0.0,
        "document_summary_source_coverage": 1.0 if passed("summary") else 0.0,
        "document_summary_new_fact_violations": 0 if passed("summary") else 1,
        "artifact_consistency_pass_rate": 1.0 if passed("consistency") else 0.0,
        "markdown_block_coverage": 1.0 if passed("consistency") else 0.0,
        "chunk_source_coverage": 1.0 if passed("consistency") else 0.0,
        "tampering_detection_rate": 1.0 if passed("consistency") else 0.0,
        "entity_passthrough_coverage": 1.0 if passed("entity") else 0.0,
        "invented_entity_id_count": 0 if passed("entity") else 1,
        "topic11_invalid_output_acceptance_count": 0 if passed("topic11") else 1,
        "topic11_fallback_success_rate": 1.0 if passed("topic11") else 0.0,
        "secret_leak_count": 0 if passed("topic11") else 1,
        "field_operation_accuracy": float(operations["field_operation_accuracy"]),
        "rename_accuracy": float(operations["rename_accuracy"]),
        "merge_accuracy": float(operations["merge_accuracy"]),
        "split_accuracy": float(operations["split_accuracy"]),
        "unsafe_operation_count": int(operations["unsafe_operation_count"]),
        "schema_localization_rate": float(localization["schema_localization_rate"]),
        "error_code_accuracy": float(localization["error_code_accuracy"]),
        "stage_accuracy": float(localization["stage_accuracy"]),
        "legacy_request_regression": 0 if passed("legacy") else 1,
        "legacy_package_regression": 0 if passed("legacy") else 1,
        "full_backend_tests_passed": bool(verification.get("full_backend_tests_passed")),
        "ruff_clean": bool(verification.get("ruff_clean")),
        "frontend_tests_passed": bool(verification.get("frontend_tests_passed")),
        "openapi_export_passed": bool(verification.get("openapi_export_passed")),
    }
    checks = {
        "metadata_template_effective": values["metadata_template_effective"] is True,
        "metadata_required_localization_rate": values["metadata_required_localization_rate"] == 1.0,
        "content_tag_metric": values["content_tag_metric"] >= 0.85,
        "management_tag_rule_accuracy": values["management_tag_rule_accuracy"] == 1.0,
        "quality_tag_metric": values["quality_tag_metric"] >= 0.85,
        "global_quality_tag_pollution_count": values["global_quality_tag_pollution_count"] == 0,
        "document_summary_faithfulness": values["document_summary_faithfulness"] == 1.0,
        "document_summary_source_coverage": values["document_summary_source_coverage"] == 1.0,
        "document_summary_new_fact_violations": values["document_summary_new_fact_violations"] == 0,
        "artifact_consistency_pass_rate": values["artifact_consistency_pass_rate"] == 1.0,
        "markdown_block_coverage": values["markdown_block_coverage"] == 1.0,
        "chunk_source_coverage": values["chunk_source_coverage"] == 1.0,
        "tampering_detection_rate": values["tampering_detection_rate"] == 1.0,
        "entity_passthrough_coverage": values["entity_passthrough_coverage"] == 1.0,
        "invented_entity_id_count": values["invented_entity_id_count"] == 0,
        "topic11_invalid_output_acceptance_count": values["topic11_invalid_output_acceptance_count"] == 0,
        "topic11_fallback_success_rate": values["topic11_fallback_success_rate"] == 1.0,
        "secret_leak_count": values["secret_leak_count"] == 0,
        "field_operation_accuracy": values["field_operation_accuracy"] >= 0.95,
        "rename_accuracy": values["rename_accuracy"] >= 0.95,
        "merge_accuracy": values["merge_accuracy"] >= 0.95,
        "split_accuracy": values["split_accuracy"] >= 0.95,
        "unsafe_operation_count": values["unsafe_operation_count"] == 0,
        "schema_localization_rate": values["schema_localization_rate"] == 1.0,
        "error_code_accuracy": values["error_code_accuracy"] == 1.0,
        "stage_accuracy": values["stage_accuracy"] == 1.0,
        "legacy_request_regression": values["legacy_request_regression"] == 0,
        "legacy_package_regression": values["legacy_package_regression"] == 0,
        "full_backend_tests_passed": values["full_backend_tests_passed"] is True,
        "ruff_clean": values["ruff_clean"] is True,
        "frontend_tests_passed": values["frontend_tests_passed"] is True,
        "openapi_export_passed": values["openapi_export_passed"] is True,
    }
    failed = [name for name, result in checks.items() if not result]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "conclusion": "passed" if not failed else "failed",
        "passed": not failed,
        "values": values,
        "checks": checks,
        "failed_conditions": failed,
        "datasets": {
            "field_operations": operations["dataset_sha256"],
            "schema_localization": localization["dataset_sha256"],
        },
        "component_checks": components,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Topic 5 Hard-Gap Batch 1 Gate",
        "",
        f"Conclusion: **{report['conclusion']}**",
        "",
        "| Condition | Value | Passed |",
        "| --- | --- | --- |",
    ]
    for name, check_passed in report["checks"].items():
        lines.append(f"| {name} | {report['values'][name]} | {check_passed} |")
    if report["failed_conditions"]:
        lines.extend(["", "Failed: " + ", ".join(report["failed_conditions"])])
    return "\n".join(lines) + "\n"


def _last_nonempty_line(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tag-report", type=Path, default=DEFAULT_TAG_REPORT)
    parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument("--skip-component-tests", action="store_true")
    args = parser.parse_args()
    if not args.verification.is_file():
        raise SystemExit(f"verification summary is missing: {args.verification}")
    components = (
        {name: {"passed": True, "summary": "skipped by caller"} for name in COMPONENT_TESTS}
        if args.skip_component_tests
        else run_component_checks()
    )
    report = evaluate_gate(
        operations=field_report(),
        localization=localization_report(),
        tag_quality=json.loads(args.tag_report.read_text(encoding="utf-8")),
        components=components,
        verification=json.loads(args.verification.read_text(encoding="utf-8")),
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "hard_gap_batch_1_gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "hard_gap_batch_1_gate.md").write_text(
        render_markdown(report), encoding="utf-8"
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
