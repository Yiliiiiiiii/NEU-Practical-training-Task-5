from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    scripts = str(path.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(f"test_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_regression_evaluator_uses_runtime_and_package_evidence() -> None:
    report = _load("eval_topic5_batch2_regressions").run_evaluation()

    assert report["status"] == "passed"
    assert report["status_truth_table_passed"] is True
    assert report["registered_validation_status_regression"] == 0
    assert report["package_failure_status_regression"] == 0
    assert report["content_json_internal_key_leak_count"] == 0
    assert report["package_recomputed_consistency_rate"] == 1.0
    assert report["package_tampering_detection_rate"] == 1.0
    assert report["nonempty_canonical_block_chunk_coverage"] == 1.0
    assert report["protected_block_integrity"] == 1.0


def test_runner_contains_all_final_evaluators() -> None:
    runner = _load("run_topic5_batch_2_verification")
    names = {spec.name for spec in runner.command_specs()}

    assert {
        "backend-tests",
        "ruff",
        "frontend-tests",
        "frontend-build",
        "openapi-drift",
        "schemapack-contract-gate",
        "evaluator-tag-quality-v2",
        "evaluator-field-operations",
        "evaluator-schema-localization",
        "evaluator-mapping-v2-dev",
        "evaluator-mapping-v2-test",
        "mapping-v2-gate",
        "evaluator-runtime-equivalence",
        "evaluator-replay",
        "evaluator-batch2-regressions",
        "evaluator-package-faults",
        "evaluator-concurrency",
        "evaluator-performance",
        "evaluator-downstream-contracts",
    } <= names


def test_github_ci_requires_actions_environment_and_exact_head(
    tmp_path: Path, monkeypatch
) -> None:
    runner = _load("run_topic5_batch_2_verification")
    record = {
        "name": "backend-tests",
        "mandatory": True,
        "passed": True,
        "status": "passed",
    }
    commit = "a" * 40

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    local = runner.write_summary(
        tmp_path / "local",
        commit_sha=commit,
        dirty=False,
        allow_dirty=False,
        records=[record],
        tool_versions={},
    )
    assert runner.json.loads(local.read_text())["github_ci_passed"] is False

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    wrong = runner.write_summary(
        tmp_path / "wrong",
        commit_sha=commit,
        dirty=False,
        allow_dirty=False,
        records=[record],
        tool_versions={},
    )
    assert runner.json.loads(wrong.read_text())["github_ci_passed"] is False

    monkeypatch.setenv("GITHUB_SHA", commit)
    exact = runner.write_summary(
        tmp_path / "exact",
        commit_sha=commit,
        dirty=False,
        allow_dirty=False,
        records=[record],
        tool_versions={},
    )
    assert runner.json.loads(exact.read_text())["github_ci_passed"] is True


def test_status_source_is_built_from_gate_and_verification_reports() -> None:
    generator = _load("generate_topic5_batch_2_status")
    gate = {
        "commit_sha": "c" * 40,
        "status": "pending_external_ci",
        "passed": False,
        "local_acceptance_passed": True,
        "failed_conditions": ["github_ci_passed"],
        "values": {
            "external_blind_status": "not_run",
            "can_claim_production_blind_0_85": False,
        },
    }
    verification = {
        "commands": [
            {"name": "backend-tests", "stdout": "999 passed in 1.0s"},
            {"name": "frontend-tests", "stdout": "24 passed"},
        ],
        "full_backend_tests_passed": True,
        "ruff_clean": True,
        "frontend_tests_passed": True,
        "frontend_build_passed": True,
        "openapi_export_passed": True,
        "schema_pack_contract_gate_passed": True,
        "github_ci_passed": False,
        "github_ci_commit_sha": None,
    }

    status = generator.build_status(gate, verification)

    assert status["commit_sha"] == "c" * 40
    assert status["status"] == "pending_external_ci"
    assert status["verification"]["backend_test_count"] == 999
    assert status["verification"]["openapi_drift"] == 0
    assert status["claims"]["external_blind_status"] == "not_run"
    assert status["claims"]["can_claim_production_blind_0_85"] is False
