"""Aggregate case-level Topic 5 Batch 2 evaluator reports into an acceptance gate."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_topic5_hard_gap_batch_1_gate import (  # noqa: E402
    _validated_evaluator_reports,
    build_evaluator_reports,
)


DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "acceptance_gate.json"
REPORT_FILENAMES = {
    "metadata": "metadata_contract.json",
    "summary": "summary_faithfulness.json",
    "consistency": "artifact_consistency.json",
    "entity": "entity_passthrough.json",
    "topic11": "topic11_adapter.json",
}


def load_evaluator_reports(report_dir: Path) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for name, filename in REPORT_FILENAMES.items():
        path = report_dir / filename
        if not path.is_file():
            raise ValueError(f"missing evaluator report: {path}")
        reports[name] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def evaluate_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    reports = _validated_evaluator_reports(reports)
    metadata = reports["metadata"]
    summary = reports["summary"]
    consistency = reports["consistency"]
    entity = reports["entity"]
    topic11 = reports["topic11"]
    values = {
        "metadata_template_effective": bool(metadata["metadata_template_effective"]),
        "metadata_required_localization_rate": float(
            metadata["metadata_required_localization_rate"]
        ),
        "document_summary_faithfulness": float(
            summary["document_summary_faithfulness"]
        ),
        "document_summary_source_coverage": float(
            summary["document_summary_source_coverage"]
        ),
        "document_summary_new_fact_violations": int(
            summary["document_summary_new_fact_violations"]
        ),
        "artifact_consistency_pass_rate": float(
            consistency["artifact_consistency_pass_rate"]
        ),
        "markdown_block_coverage": float(consistency["markdown_block_coverage"]),
        "chunk_source_coverage": float(consistency["chunk_source_coverage"]),
        "tampering_detection_rate": float(consistency["tampering_detection_rate"]),
        "entity_passthrough_coverage": float(entity["entity_passthrough_coverage"]),
        "invented_entity_id_count": int(entity["invented_entity_id_count"]),
        "topic11_fallback_success_rate": float(
            topic11["topic11_fallback_success_rate"]
        ),
        "topic11_invalid_output_acceptance_count": int(
            topic11["topic11_invalid_output_acceptance_count"]
        ),
        "secret_leak_count": int(topic11["secret_leak_count"]),
        "legacy_compatibility_rate": float(topic11["legacy_compatibility_rate"]),
    }
    checks = {
        **{
            f"{name}_cases_passed": report["passed_count"] == report["case_count"]
            for name, report in reports.items()
        },
        "metadata_template_effective": values["metadata_template_effective"] is True,
        "metadata_required_localization_rate": (
            values["metadata_required_localization_rate"] == 1.0
        ),
        "document_summary_faithfulness": (
            values["document_summary_faithfulness"] == 1.0
        ),
        "document_summary_source_coverage": (
            values["document_summary_source_coverage"] == 1.0
        ),
        "document_summary_new_fact_violations": (
            values["document_summary_new_fact_violations"] == 0
        ),
        "artifact_consistency_pass_rate": (
            values["artifact_consistency_pass_rate"] == 1.0
        ),
        "markdown_block_coverage": values["markdown_block_coverage"] == 1.0,
        "chunk_source_coverage": values["chunk_source_coverage"] == 1.0,
        "tampering_detection_rate": values["tampering_detection_rate"] == 1.0,
        "entity_passthrough_coverage": values["entity_passthrough_coverage"] == 1.0,
        "invented_entity_id_count": values["invented_entity_id_count"] == 0,
        "topic11_fallback_success_rate": values["topic11_fallback_success_rate"] == 1.0,
        "topic11_invalid_output_acceptance_count": (
            values["topic11_invalid_output_acceptance_count"] == 0
        ),
        "secret_leak_count": values["secret_leak_count"] == 0,
        "legacy_compatibility_rate": values["legacy_compatibility_rate"] == 1.0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": not failed,
        "conclusion": "passed" if not failed else "failed",
        "values": values,
        "checks": checks,
        "failed_conditions": failed,
        "datasets": {
            name: {
                "dataset_id": report["dataset_id"],
                "dataset_version": report["dataset_version"],
                "dataset_sha256": report["dataset_sha256"],
                "commit_sha": report["commit_sha"],
                "case_count": report["case_count"],
                "passed_count": report["passed_count"],
            }
            for name, report in reports.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    reports = (
        load_evaluator_reports(args.report_dir)
        if args.report_dir is not None
        else build_evaluator_reports()
    )
    gate = evaluate_reports(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(0 if gate["passed"] else 1)


if __name__ == "__main__":
    main()
