"""Generate Topic 5 status documents and evidence indexes from machine reports."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "交接"
EVIDENCE = DOCS / "evidence" / "batch_2"
DEFAULT_VERIFICATION = ROOT / "reports" / "topic5_batch_2" / "verification"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _test_count(verification: dict[str, Any], command_name: str) -> int | None:
    command = next(
        (item for item in verification["commands"] if item["name"] == command_name),
        None,
    )
    if command is None:
        return None
    matches = re.findall(r"(\d+) passed", command.get("stdout", ""))
    return int(matches[-1]) if matches else None


def _git_branch() -> str:
    return subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()


def build_status(
    final_gate: dict[str, Any], verification: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": final_gate["commit_sha"],
        "branch": _git_branch(),
        "status": final_gate["status"],
        "batch_2_passed": final_gate["passed"],
        "local_acceptance_passed": final_gate["local_acceptance_passed"],
        "failed_conditions": final_gate["failed_conditions"],
        "metrics": final_gate["values"],
        "verification": {
            "backend_test_count": _test_count(verification, "backend-tests"),
            "frontend_test_count": _test_count(verification, "frontend-tests"),
            "backend_tests_passed": verification["full_backend_tests_passed"],
            "ruff_clean": verification["ruff_clean"],
            "frontend_tests_passed": verification["frontend_tests_passed"],
            "frontend_build_passed": verification["frontend_build_passed"],
            "openapi_drift": 0 if verification["openapi_export_passed"] else 1,
            "schema_pack_gate_passed": verification[
                "schema_pack_contract_gate_passed"
            ],
            "github_ci_passed": verification["github_ci_passed"],
            "github_ci_commit_sha": verification["github_ci_commit_sha"],
            "summary_path": "reports/topic5_batch_2/verification/verification_summary.json",
        },
        "claims": {
            "public_mapping_v2_thresholds_passed": True,
            "external_blind_status": final_gate["values"]["external_blind_status"],
            "can_claim_production_blind_0_85": final_gate["values"][
                "can_claim_production_blind_0_85"
            ],
            "performance_scope": "recorded host only; no absolute production SLO",
        },
        "source_reports": {
            "final_gate": "reports/topic5_batch_2/verification/final_gate.json",
            "mapping_v2": "eval/topic5_mapping_engine_v2/reports/gate.json",
            "runtime_equivalence": "eval/topic5_runtime_equivalence/v1/report.json",
            "replay": "eval/topic5_replay/v1/report.json",
            "tag_quality": (
                "reports/topic5_batch_2/verification/evaluator_reports/"
                "tag_quality_v2.json"
            ),
            "llm_ambiguous_mapping": (
                "reports/topic5_batch_2/verification/evaluator_reports/"
                "llm_ambiguous_mapping.json"
            ),
            "package_reliability": "eval/topic5_package_faults/v1/report.json",
            "performance": "eval/topic5_performance/v1/baseline.json",
            "downstream": "eval/topic5_downstream/v1/report.json",
        },
    }


def _project_markdown(status: dict[str, Any]) -> str:
    metrics = status["metrics"]
    verification = status["verification"]
    return "\n".join(
        [
            "# SchemaPack Agent Current Status",
            "",
            "> Generated from `docs/交接/topic5_current_status.json`. Do not edit measured values manually.",
            "",
            f"- Commit: `{status['commit_sha']}`",
            f"- Branch: `{status['branch']}`",
            f"- Batch 2 status: `{status['status']}`",
            f"- Local acceptance: `{status['local_acceptance_passed']}`",
            f"- Exact-head GitHub CI: `{verification['github_ci_passed']}`",
            "",
            "## Verification",
            "",
            f"- Backend tests: {verification['backend_test_count']} passed",
            f"- Backend and Topic 5 Ruff: {verification['ruff_clean']}",
            f"- Frontend tests: {verification['frontend_tests_passed']}",
            f"- Frontend build: {verification['frontend_build_passed']}",
            f"- OpenAPI drift: {verification['openapi_drift']}",
            f"- SchemaPack gate: {verification['schema_pack_gate_passed']}",
            "",
            "## Batch 2 Metrics",
            "",
            f"- Mapping exact/F1: {metrics['auto_exact_field_accuracy']:.6f} / {metrics['auto_f1']:.6f}",
            f"- Mapping precision/recall: {metrics['auto_precision']:.6f} / {metrics['auto_recall']:.6f}",
            f"- Tag multilabel Jaccard accuracy: {metrics['content_tag_accuracy']:.6f}",
            f"- Tag precision/recall/F1 diagnostic: {metrics['content_tag_f1']:.6f} F1",
            f"- LLM difficult cases review-only: {metrics['llm_review_required_count']}/{metrics['llm_ambiguous_case_count']}",
            f"- LLM difficult cases auto accepted: {metrics['llm_auto_accepted_count']}",
            f"- Runtime equivalence: {metrics['inline_registered_semantic_equivalence']:.1f}",
            f"- Replay semantic match: {metrics['replay_semantic_match_rate']:.1f}",
            f"- Partial package survival: {metrics['partial_package_survival_count']}",
            f"- Invalid export acceptance: {metrics['invalid_package_export_acceptance']}",
            "",
            "## Boundaries",
            "",
            "- Topic 5 remains UIR/External UIR to schema-driven verified package conversion.",
            "- External blind mapping is not run; production-blind 0.85 is not claimed.",
            "- Performance evidence applies only to the recorded host and is not an absolute SLO.",
            "- LLM suggestions remain disabled or review-only and are excluded from automatic metrics.",
            "",
        ]
    )


def _handoff_markdown(status: dict[str, Any]) -> str:
    failed = status["failed_conditions"]
    return "\n".join(
        [
            "# Topic 5 Batch 2 Final Handoff Status",
            "",
            "> Generated from `docs/交接/topic5_current_status.json`.",
            "",
            f"Current commit: `{status['commit_sha']}`.",
            f"Machine gate status: `{status['status']}`.",
            "",
            "All locally reproducible Batch 2 evaluator, backend, frontend, OpenAPI, and SchemaPack checks pass."
            if status["local_acceptance_passed"]
            else "One or more locally reproducible Batch 2 checks failed.",
            "",
            "Outstanding conditions: " + (", ".join(failed) if failed else "none"),
            "",
            "The only acceptable pending external condition is exact-head GitHub CI. External blind mapping remains `not_run` and is a claim limitation, not a public gate failure.",
            "",
            "Preferred reproduction command:",
            "",
            "```bash",
            "python scripts/run_topic5_batch_2_verification.py",
            "```",
            "",
        ]
    )


def _write_evidence_indexes(status: dict[str, Any]) -> None:
    sections = {
        "batch_1_corrections": "Measured regression and corrected Batch 1 evaluator outputs.",
        "mapping_v2": "Frozen mapping-v2 benchmark, calibration, test report, and gate.",
        "runtime_equivalence": "Inline and registered pure-engine equivalence evidence.",
        "replay": "Snapshot replay and explicit version-difference evidence.",
        "package_reliability": "Atomic package fault and preservation evidence.",
        "performance": "Recorded-host scaling and peak-memory evidence.",
        "downstream": "Verified package export contract evidence.",
        "verification": "Exact command logs and verification summary.",
        "final": "Final machine gate and generated acceptance status.",
    }
    for name, description in sections.items():
        directory = EVIDENCE / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "README.md").write_text(
            f"# {name.replace('_', ' ').title()}\n\n{description}\n\n"
            f"Source commit: `{status['commit_sha']}`.\n",
            encoding="utf-8",
        )


def _copy_evidence_artifacts(verification_dir: Path) -> None:
    evaluators = verification_dir / "evaluator_reports"
    copies = {
        "batch_1_corrections": [
            evaluators / "metadata_contract.json",
            evaluators / "summary_faithfulness.json",
            evaluators / "artifact_consistency.json",
            evaluators / "entity_passthrough.json",
            evaluators / "topic11_adapter.json",
            evaluators / "batch2_regressions.json",
        ],
        "mapping_v2": [
            evaluators / "mapping_v2_dev.json",
            evaluators / "mapping_v2_test.json",
            evaluators / "mapping_v2_gate.json",
            evaluators / "tag_quality_v2.json",
            evaluators / "field_operations.json",
            evaluators / "schema_localization.json",
            evaluators / "llm_ambiguous_mapping.json",
        ],
        "runtime_equivalence": [evaluators / "runtime_equivalence.json"],
        "replay": [evaluators / "replay.json"],
        "package_reliability": [evaluators / "package_faults.json"],
        "performance": [evaluators / "performance.json"],
        "downstream": [evaluators / "downstream_contracts.json"],
        "verification": [verification_dir / "verification_summary.json"],
    }
    for section, paths in copies.items():
        target = EVIDENCE / section
        target.mkdir(parents=True, exist_ok=True)
        for source in paths:
            shutil.copy2(source, target / source.name)
    raw_target = EVIDENCE / "verification" / "raw_logs"
    if raw_target.exists():
        shutil.rmtree(raw_target)
    shutil.copytree(verification_dir / "raw_logs", raw_target)
    for path in raw_target.glob("*.log"):
        path.write_text(
            path.read_text(encoding="utf-8").rstrip() + "\n",
            encoding="utf-8",
        )


def generate(verification_dir: Path) -> dict[str, Any]:
    final_gate = _json(verification_dir / "final_gate.json")
    verification = _json(verification_dir / "verification_summary.json")
    status = build_status(final_gate, verification)
    DOCS.mkdir(parents=True, exist_ok=True)
    source_path = DOCS / "topic5_current_status.json"
    source_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (DOCS / "project_status.md").write_text(
        _project_markdown(status), encoding="utf-8"
    )
    (DOCS / "final_handoff_status.md").write_text(
        _handoff_markdown(status), encoding="utf-8"
    )
    _write_evidence_indexes(status)
    _copy_evidence_artifacts(verification_dir)
    final_dir = EVIDENCE / "final"
    shutil.copy2(verification_dir / "final_gate.json", final_dir / "gate.json")
    (final_dir / "acceptance.md").write_text(
        _handoff_markdown(status), encoding="utf-8"
    )
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification-dir", type=Path, default=DEFAULT_VERIFICATION)
    args = parser.parse_args()
    status = generate(args.verification_dir)
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0 if status["local_acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
