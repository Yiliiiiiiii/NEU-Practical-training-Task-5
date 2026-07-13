"""Aggregate evaluator and exact-head verification evidence for Topic 5 Batch 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "topic5_batch_2" / "verification"
DEFAULT_OUTPUT = ROOT / "docs" / "交接" / "evidence" / "batch_2" / "final" / "gate.json"


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing report: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"report must contain an object: {path}")
    return value


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _tag_gold_frozen() -> bool:
    root = ROOT / "eval" / "topic5_tag_quality" / "v2"
    manifest_path = root / "manifest.json"
    expected_path = root.parent / "v2.manifest.sha256"
    manifest = _json(manifest_path)
    if manifest.get("immutable") is not True:
        return False
    expected = expected_path.read_text(encoding="utf-8").strip()
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != expected:
        return False
    return all(
        hashlib.sha256((root / filename).read_bytes()).hexdigest() == digest
        for filename, digest in manifest.get("files", {}).items()
    )


def _raw_log_missing_count(verification: dict[str, Any]) -> int:
    missing = 0
    for command in verification.get("commands", []):
        raw = command.get("raw_log")
        path = Path(raw) if isinstance(raw, str) and raw else None
        if path is None or not path.is_file() or path.stat().st_size == 0:
            missing += 1
    return missing


def evaluate_gate(report_dir: Path, verification_path: Path) -> dict[str, Any]:
    evaluator_dir = report_dir / "evaluator_reports"
    reports = {
        "metadata": _json(evaluator_dir / "metadata_contract.json"),
        "summary": _json(evaluator_dir / "summary_faithfulness.json"),
        "artifact": _json(evaluator_dir / "artifact_consistency.json"),
        "entity": _json(evaluator_dir / "entity_passthrough.json"),
        "topic11": _json(evaluator_dir / "topic11_adapter.json"),
        "tag": _json(evaluator_dir / "tag_quality_v2.json"),
        "llm": _json(evaluator_dir / "llm_ambiguous_mapping.json"),
        "operations": _json(evaluator_dir / "field_operations.json"),
        "localization": _json(evaluator_dir / "schema_localization.json"),
        "regressions": _json(evaluator_dir / "batch2_regressions.json"),
        "performance": _json(evaluator_dir / "performance.json"),
        "concurrency": _json(evaluator_dir / "concurrency.json"),
        "faults": _json(evaluator_dir / "package_faults.json"),
        "downstream": _json(evaluator_dir / "downstream_contracts.json"),
    }
    mapping = _json(ROOT / "eval" / "topic5_mapping_engine_v2" / "reports" / "gate.json")
    runtime = _json(ROOT / "eval" / "topic5_runtime_equivalence" / "v1" / "report.json")
    replay = _json(ROOT / "eval" / "topic5_replay" / "v1" / "report.json")
    verification = _json(verification_path)
    metrics = mapping["test_metrics"]
    tag_metrics = reports["tag"]["metrics"]
    current_head = _git_head()
    quantitative_sources = {
        name: "evaluator_report" for name in reports
    } | {
        "mapping": "evaluator_report",
        "runtime": "evaluator_report",
        "replay": "evaluator_report",
    }
    values = {
        "batch1_proxy_metric_count": sum(
            source != "evaluator_report" for source in quantitative_sources.values()
        ),
        "raw_verification_log_missing_count": _raw_log_missing_count(verification),
        "status_truth_table_passed": reports["regressions"]["status_truth_table_passed"],
        "registered_validation_status_regression": reports["regressions"][
            "registered_validation_status_regression"
        ],
        "package_failure_status_regression": reports["regressions"][
            "package_failure_status_regression"
        ],
        "content_json_internal_key_leak_count": reports["regressions"][
            "content_json_internal_key_leak_count"
        ],
        "tag_gold_frozen": _tag_gold_frozen(),
        "content_tag_accuracy": tag_metrics["content_semantic"]["accuracy"],
        "content_tag_f1": tag_metrics["content_semantic"]["f1"],
        "management_rule_correctness": tag_metrics["management_rule_correctness"][
            "rate"
        ],
        "management_trace_correctness": tag_metrics[
            "management_trace_correctness"
        ]["rate"],
        "management_scope_correctness": tag_metrics[
            "management_scope_correctness"
        ]["rate"],
        "quality_scope_correctness": tag_metrics["quality_scope_correctness"]["rate"],
        "unknown_tag_count": tag_metrics["unknown_tag_count"],
        "llm_ambiguous_case_count": reports["llm"]["metrics"][
            "ambiguous_case_count"
        ],
        "llm_fallback_exercised_count": reports["llm"]["metrics"][
            "llm_fallback_exercised_count"
        ],
        "llm_review_required_count": reports["llm"]["metrics"][
            "review_required_count"
        ],
        "llm_auto_accepted_count": reports["llm"]["metrics"][
            "auto_accepted_count"
        ],
        "llm_confidence_bound_violations": reports["llm"]["metrics"][
            "confidence_bound_violations"
        ],
        "llm_missing_reason_count": reports["llm"]["metrics"][
            "missing_reason_count"
        ],
        "llm_missing_evidence_count": reports["llm"]["metrics"][
            "missing_evidence_count"
        ],
        "llm_production_rule_catalog_unchanged": reports["llm"]["metrics"][
            "production_rule_catalog_unchanged"
        ],
        "metadata_effectiveness": reports["metadata"][
            "metadata_template_effectiveness_rate"
        ],
        "metadata_localization": reports["metadata"][
            "metadata_required_localization_rate"
        ],
        "summary_faithfulness": reports["summary"][
            "document_summary_faithfulness"
        ],
        "summary_source_coverage": reports["summary"][
            "document_summary_source_coverage"
        ],
        "summary_new_fact_violations": reports["summary"][
            "document_summary_new_fact_violations"
        ],
        "artifact_consistency_rate": reports["artifact"][
            "artifact_consistency_pass_rate"
        ],
        "package_recomputed_consistency_rate": reports["regressions"][
            "package_recomputed_consistency_rate"
        ],
        "tampering_detection_rate": min(
            reports["artifact"]["tampering_detection_rate"],
            reports["regressions"]["package_tampering_detection_rate"],
        ),
        "nonempty_canonical_block_chunk_coverage": reports["regressions"][
            "nonempty_canonical_block_chunk_coverage"
        ],
        "protected_block_integrity": reports["regressions"][
            "protected_block_integrity"
        ],
        "invalid_topic11_output_acceptance": reports["topic11"][
            "topic11_invalid_output_acceptance_count"
        ],
        "invented_entity_id_count": reports["entity"]["invented_entity_id_count"],
        "entity_source_coverage": reports["entity"]["entity_passthrough_coverage"],
        "auto_exact_field_accuracy": metrics["auto_exact_field_accuracy"],
        "auto_precision": metrics["auto_precision"],
        "auto_recall": metrics["auto_recall"],
        "auto_f1": metrics["auto_f1"],
        "macro_schema_f1": metrics["macro_f1_by_schema"],
        "required_present_field_recall": metrics["required_present_field_recall"],
        "mapping_negative_pair_violations": metrics["negative_pair_violation_count"],
        "review_required_rate": metrics["review_required_rate"],
        "field_operation_accuracy": reports["operations"]["field_operation_accuracy"],
        "schema_localization_rate": reports["localization"]["schema_localization_rate"],
        "inline_registered_semantic_equivalence": runtime[
            "inline_registered_semantic_equivalence"
        ],
        "replay_semantic_match_rate": replay["replay_semantic_match_rate"],
        "partial_package_survival_count": reports["faults"][
            "partial_package_survival_count"
        ],
        "invalid_package_export_acceptance": reports["downstream"][
            "invalid_package_export_acceptance"
        ],
        "backend_tests_passed": verification.get("full_backend_tests_passed", False),
        "ruff_clean": verification.get("ruff_clean", False),
        "frontend_tests_passed": verification.get("frontend_tests_passed", False),
        "frontend_build_passed": verification.get("frontend_build_passed", False),
        "openapi_drift": 0 if verification.get("openapi_export_passed") else 1,
        "schema_pack_gate_passed": verification.get(
            "schema_pack_contract_gate_passed", False
        ),
        "github_ci_passed": bool(verification.get("github_ci_passed"))
        and verification.get("github_ci_commit_sha") == current_head,
        "performance_evidence_passed": reports["performance"]["status"] == "passed",
        "concurrency_evidence_passed": reports["concurrency"]["status"] == "passed",
        "downstream_evidence_passed": reports["downstream"]["status"] == "passed",
        "external_blind_status": mapping["external_blind_status"],
        "can_claim_production_blind_0_85": mapping[
            "can_claim_production_blind_0_85"
        ],
    }
    checks = {
        "batch1_proxy_metric_count": values["batch1_proxy_metric_count"] == 0,
        "raw_verification_log_missing_count": values[
            "raw_verification_log_missing_count"
        ]
        == 0,
        "status_truth_table_passed": values["status_truth_table_passed"] is True,
        "registered_validation_status_regression": values[
            "registered_validation_status_regression"
        ]
        == 0,
        "package_failure_status_regression": values[
            "package_failure_status_regression"
        ]
        == 0,
        "content_json_internal_key_leak_count": values[
            "content_json_internal_key_leak_count"
        ]
        == 0,
        "tag_gold_frozen": values["tag_gold_frozen"] is True,
        "content_tag_accuracy": values["content_tag_accuracy"] >= 0.85,
        "content_tag_f1": values["content_tag_f1"] >= 0.85,
        "management_rule_correctness": values["management_rule_correctness"] == 1.0,
        "management_trace_correctness": values["management_trace_correctness"]
        == 1.0,
        "management_scope_correctness": values["management_scope_correctness"]
        == 1.0,
        "quality_scope_correctness": values["quality_scope_correctness"] == 1.0,
        "unknown_tag_count": values["unknown_tag_count"] == 0,
        "llm_fallback_exercised": values["llm_ambiguous_case_count"] >= 1
        and values["llm_fallback_exercised_count"]
        == values["llm_ambiguous_case_count"],
        "llm_review_only": values["llm_review_required_count"]
        == values["llm_ambiguous_case_count"]
        and values["llm_auto_accepted_count"] == 0,
        "llm_evidence_complete": values["llm_confidence_bound_violations"] == 0
        and values["llm_missing_reason_count"] == 0
        and values["llm_missing_evidence_count"] == 0,
        "llm_production_rule_catalog_unchanged": values[
            "llm_production_rule_catalog_unchanged"
        ]
        is True,
        "metadata_effectiveness": values["metadata_effectiveness"] == 1.0,
        "metadata_localization": values["metadata_localization"] == 1.0,
        "summary_faithfulness": values["summary_faithfulness"] == 1.0,
        "summary_source_coverage": values["summary_source_coverage"] == 1.0,
        "summary_new_fact_violations": values["summary_new_fact_violations"] == 0,
        "artifact_consistency_rate": values["artifact_consistency_rate"] == 1.0,
        "package_recomputed_consistency_rate": values[
            "package_recomputed_consistency_rate"
        ]
        == 1.0,
        "tampering_detection_rate": values["tampering_detection_rate"] == 1.0,
        "nonempty_canonical_block_chunk_coverage": values[
            "nonempty_canonical_block_chunk_coverage"
        ]
        == 1.0,
        "protected_block_integrity": values["protected_block_integrity"] == 1.0,
        "invalid_topic11_output_acceptance": values[
            "invalid_topic11_output_acceptance"
        ]
        == 0,
        "invented_entity_id_count": values["invented_entity_id_count"] == 0,
        "entity_source_coverage": values["entity_source_coverage"] == 1.0,
        "auto_exact_field_accuracy": values["auto_exact_field_accuracy"] >= 0.85,
        "auto_precision": values["auto_precision"] >= 0.90,
        "auto_recall": values["auto_recall"] >= 0.85,
        "auto_f1": values["auto_f1"] >= 0.87,
        "macro_schema_f1": values["macro_schema_f1"] >= 0.82,
        "required_present_field_recall": values[
            "required_present_field_recall"
        ]
        >= 0.95,
        "mapping_negative_pair_violations": values[
            "mapping_negative_pair_violations"
        ]
        == 0,
        "review_required_rate": values["review_required_rate"] <= 0.20,
        "field_operation_accuracy": values["field_operation_accuracy"] >= 0.95,
        "schema_localization_rate": values["schema_localization_rate"] == 1.0,
        "inline_registered_semantic_equivalence": values[
            "inline_registered_semantic_equivalence"
        ]
        == 1.0,
        "replay_semantic_match_rate": values["replay_semantic_match_rate"] == 1.0,
        "partial_package_survival_count": values[
            "partial_package_survival_count"
        ]
        == 0,
        "invalid_package_export_acceptance": values[
            "invalid_package_export_acceptance"
        ]
        == 0,
        "backend_tests_passed": values["backend_tests_passed"] is True,
        "ruff_clean": values["ruff_clean"] is True,
        "frontend_tests_passed": values["frontend_tests_passed"] is True,
        "frontend_build_passed": values["frontend_build_passed"] is True,
        "openapi_drift": values["openapi_drift"] == 0,
        "schema_pack_gate_passed": values["schema_pack_gate_passed"] is True,
        "github_ci_passed": values["github_ci_passed"] is True,
        "performance_evidence_passed": values["performance_evidence_passed"] is True,
        "concurrency_evidence_passed": values["concurrency_evidence_passed"] is True,
        "downstream_evidence_passed": values["downstream_evidence_passed"] is True,
        "external_blind_claim_boundary": values["external_blind_status"] == "not_run"
        and values["can_claim_production_blind_0_85"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    external_only = failed == ["github_ci_passed"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": current_head,
        "status": (
            "passed"
            if not failed
            else "pending_external_ci"
            if external_only
            else "failed"
        ),
        "passed": not failed,
        "local_acceptance_passed": not failed or external_only,
        "values": values,
        "checks": checks,
        "failed_conditions": failed,
        "quantitative_sources": quantitative_sources,
        "verification_summary": str(verification_path.resolve()),
        "claim_boundary": (
            "Frozen public mapping-v2 evidence only; external blind is not run and "
            "exact-head GitHub CI is accepted only from the GitHub Actions environment."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--verification", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-pending-github-ci", action="store_true")
    args = parser.parse_args()
    verification = args.verification or args.report_dir / "verification_summary.json"
    report = evaluate_gate(args.report_dir, verification)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["passed"] or (
        args.allow_pending_github_ci and report["status"] == "pending_external_ci"
    ):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
