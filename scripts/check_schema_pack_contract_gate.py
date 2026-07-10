"""Run the Phase 3 SchemaPack contract gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_topic5_alignment_gate import check as check_alignment  # noqa: E402
from scripts.check_topic5_mapping_quality_gate import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_THRESHOLDS,
    build_gate_report as build_mapping_gate_report,
    render_markdown as render_mapping_markdown,
    run_split_reports,
)
from scripts.eval_schema_pack_contracts import (  # noqa: E402
    DEFAULT_EXAMPLES,
    evaluate_all,
)
from scripts.eval_topic5_standard_uir_mapping import (  # noqa: E402
    write_json as write_mapping_json,
    write_markdown as write_mapping_markdown,
)


DEFAULT_JSON = ROOT / "reports" / "schema_pack_contract_gate_report.json"
DEFAULT_MD = ROOT / "reports" / "schema_pack_contract_gate_report.md"


def build_gate_report(
    contract_report: dict[str, Any],
    phase2_mapping_report: dict[str, Any],
    alignment_report: dict[str, Any],
) -> dict[str, Any]:
    items = contract_report.get("items", [])
    checks = {
        "manifest_contracts": "passed"
        if items and all(item.get("contract_valid") for item in items)
        else "failed",
        "asset_integrity": "passed"
        if items and all(not item.get("contract_errors") for item in items)
        else "failed",
        "cross_file_consistency": "passed"
        if items and all(item.get("contract_valid") for item in items)
        else "failed",
        "positive_examples": "passed"
        if items
        and all(
            int(item.get("positive_examples_total", 0)) > 0
            and item.get("positive_examples_passed")
            == item.get("positive_examples_total")
            for item in items
        )
        else "failed",
        "badcase_detection": "passed"
        if items
        and all(
            int(item.get("badcases_total", 0)) > 0
            and item.get("badcases_passed") == item.get("badcases_total")
            for item in items
        )
        else "failed",
        "package_1_1_compatibility": "passed"
        if items
        and all(item.get("package_verifier_passed") is True for item in items)
        and any(
            item.get("package_with_assertion_report_verified") is True
            for item in items
        )
        and any(
            item.get("package_without_assertion_report_verified") is True
            for item in items
        )
        else "failed",
        "phase2_mapping_gate": "passed"
        if phase2_mapping_report.get("status") == "passed"
        else "failed",
        "topic5_alignment_gate": "passed"
        if alignment_report.get("status") == "passed"
        else "failed",
    }
    failed = [name for name, status in checks.items() if status == "failed"]
    for item in items:
        schema_pack_id = str(item.get("schema_pack_id") or "unknown")
        failed.extend(
            f"{schema_pack_id}:{failure}"
            for failure in item.get("unexpected_assertion_failures", [])
        )
        failed.extend(
            f"{schema_pack_id}:{error}"
            for error in item.get("contract_errors", [])
        )
    warnings = [
        *phase2_mapping_report.get("warnings", []),
        *alignment_report.get("warnings", []),
    ]
    return {
        "status": "passed" if not failed else "failed",
        "checks": checks,
        "failed_checks": failed,
        "warnings": warnings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SchemaPack Contract Gate Report",
        "",
        f"- status: {report['status']}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {name}: {status}" for name, status in report["checks"].items())
    if report["failed_checks"]:
        lines.extend(["", "## Failed Checks", ""])
        lines.extend(f"- {item}" for item in report["failed_checks"])
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def gate_exit_code(report: dict[str, Any], *, fail_on_gate: bool) -> int:
    return int(fail_on_gate and report.get("status") != "passed")


def run_gate() -> dict[str, Any]:
    contract_report = evaluate_all(DEFAULT_EXAMPLES, verify_package=True)
    split_reports = run_split_reports(
        dataset_root=DEFAULT_DATASET,
        mode="global_assignment",
        thresholds=DEFAULT_THRESHOLDS,
        verify_package=True,
    )
    mapping_report = build_mapping_gate_report(
        split_reports,
        mode="global_assignment",
        verify_package=True,
    )
    write_mapping_json(
        ROOT / "reports" / "topic5_mapping_quality_gate_report.json",
        mapping_report,
    )
    write_mapping_markdown(
        ROOT / "reports" / "topic5_mapping_quality_gate_report.md",
        render_mapping_markdown(mapping_report),
    )
    return build_gate_report(contract_report, mapping_report, check_alignment())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--fail-on-gate", action="store_true")
    args = parser.parse_args()
    try:
        report = run_gate()
    except Exception as exc:
        report = {
            "status": "failed",
            "checks": {},
            "failed_checks": [f"gate_execution_error:{exc}"],
            "warnings": [],
        }
    write_reports(report, args.out, args.markdown)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(gate_exit_code(report, fail_on_gate=args.fail_on_gate))


if __name__ == "__main__":
    main()
