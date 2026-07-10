from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_REPORT_FIELDS = {
    "dataset_id",
    "dataset_version",
    "dataset_sha256",
    "commit_sha",
    "case_count",
    "passed_count",
    "failed_cases",
    "reproduction_command",
    "claim_boundary",
}
EVALUATORS = {
    "metadata_contract": {
        "metrics": {
            "metadata_template_effectiveness_rate": 1.0,
            "metadata_required_localization_rate": 1.0,
        }
    },
    "summary_faithfulness": {
        "metrics": {
            "document_summary_faithfulness": 1.0,
            "document_summary_source_coverage": 1.0,
            "document_summary_new_fact_violations": 0,
        }
    },
    "artifact_consistency": {
        "metrics": {
            "artifact_consistency_pass_rate": 1.0,
            "markdown_block_coverage": 1.0,
            "chunk_source_coverage": 1.0,
            "tampering_detection_rate": 1.0,
        }
    },
    "entity_passthrough": {
        "metrics": {
            "entity_passthrough_coverage": 1.0,
            "invented_entity_id_count": 0,
        }
    },
    "topic11_adapter": {
        "metrics": {
            "topic11_fallback_success_rate": 1.0,
            "topic11_invalid_output_acceptance_count": 0,
            "secret_leak_count": 0,
            "legacy_compatibility_rate": 1.0,
        }
    },
}


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"eval_topic5_{name}.py"
    assert path.is_file(), f"missing evaluator: {path}"
    spec = importlib.util.spec_from_file_location(f"eval_topic5_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("name", "contract"), EVALUATORS.items())
def test_batch_2_evaluator_report_contract(name: str, contract: dict) -> None:
    module = _load_script(name)
    report = module.build_report()
    fixture_path = ROOT / "eval" / f"topic5_{name}" / "v2" / "cases.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert REQUIRED_REPORT_FIELDS <= report.keys()
    assert report["dataset_id"] == fixture["dataset_id"]
    assert report["dataset_version"] == fixture["version"]
    assert report["dataset_sha256"] == hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    assert report["case_count"] == len(fixture["cases"])
    assert report["case_count"] > 0
    assert report["passed_count"] == report["case_count"]
    assert report["failed_cases"] == []
    assert len(report["commit_sha"]) == 40
    assert report["reproduction_command"]
    assert report["claim_boundary"]
    for metric, expected in contract["metrics"].items():
        assert report[metric] == expected


def test_metadata_evaluator_counts_a_declared_case_failure(tmp_path: Path) -> None:
    module = _load_script("metadata_contract")
    fixture = json.loads(module.DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    fixture["cases"][0]["expected_document_metadata"] = {"wrong": "value"}
    mutated = tmp_path / "cases.json"
    mutated.write_text(json.dumps(fixture), encoding="utf-8")

    report = module.build_report(mutated)

    assert report["case_count"] == len(fixture["cases"])
    assert report["passed_count"] == report["case_count"] - 1
    assert [case["case_id"] for case in report["failed_cases"]] == [
        fixture["cases"][0]["case_id"]
    ]


@pytest.mark.parametrize(
    ("report_name", "field", "tampered_value"),
    [
        ("metadata", "dataset_id", "forged_dataset"),
        ("metadata", "dataset_version", "0.0.0"),
        ("metadata", "dataset_sha256", "f" * 64),
        ("metadata", "commit_sha", "0" * 40),
        ("metadata", "case_count", 999),
        ("metadata", "passed_count", 0),
        ("metadata", "cases", []),
        ("metadata", "failed_cases", [{"case_id": "forged-case"}]),
        ("metadata", "reproduction_command", "python forged.py"),
        ("metadata", "claim_boundary", "forged claim"),
        ("metadata", "metadata_template_effectiveness_rate", 0.0),
        ("summary", "document_summary_new_fact_violations", 99),
        ("consistency", "tampering_detection_rate", 0.0),
        ("entity", "invented_entity_id_count", 1),
        ("topic11", "secret_leak_count", 1),
    ],
)
def test_evaluator_report_validation_recomputes_registered_builder_output(
    report_name: str,
    field: str,
    tampered_value: object,
) -> None:
    from scripts.check_topic5_hard_gap_batch_1_gate import (
        _validated_evaluator_reports,
        build_evaluator_reports,
    )

    reports = build_evaluator_reports()
    reports[report_name][field] = tampered_value

    with pytest.raises(ValueError, match=rf"{report_name}.*{field}"):
        _validated_evaluator_reports(reports)


def test_evaluator_report_validation_allows_generated_at_to_differ() -> None:
    from scripts.check_topic5_hard_gap_batch_1_gate import (
        _validated_evaluator_reports,
        build_evaluator_reports,
    )

    reports = build_evaluator_reports()
    reports["metadata"]["generated_at"] = "caller-recorded-timestamp"

    assert _validated_evaluator_reports(reports) is reports


def test_gate_uses_evaluator_reports_and_rejects_component_proxies() -> None:
    from scripts.check_topic5_hard_gap_batch_1_gate import evaluate_gate

    evaluator_reports = {
        "metadata": _load_script("metadata_contract").build_report(),
        "summary": _load_script("summary_faithfulness").build_report(),
        "consistency": _load_script("artifact_consistency").build_report(),
        "entity": _load_script("entity_passthrough").build_report(),
        "topic11": _load_script("topic11_adapter").build_report(),
    }
    operations = {
        "field_operation_accuracy": 1.0,
        "rename_accuracy": 1.0,
        "merge_accuracy": 1.0,
        "split_accuracy": 1.0,
        "unsafe_operation_count": 0,
        "dataset_sha256": "operations",
    }
    localization = {
        "schema_localization_rate": 1.0,
        "error_code_accuracy": 1.0,
        "stage_accuracy": 1.0,
        "dataset_sha256": "localization",
    }
    tag_quality = {
        "metrics": {
            "content_tag_f1": 1.0,
            "management_tag_f1": 1.0,
            "quality_tag_f1": 1.0,
            "unknown_tag_count": 0,
        }
    }
    verification = {
        "full_backend_tests_passed": True,
        "ruff_clean": True,
        "frontend_tests_passed": True,
        "openapi_export_passed": True,
    }
    components = {
        name: {"passed": True}
        for name in ("metadata", "summary", "consistency", "entity", "topic11", "legacy")
    }

    passed = evaluate_gate(
        operations=operations,
        localization=localization,
        tag_quality=tag_quality,
        components=components,
        evaluator_reports=evaluator_reports,
        verification=verification,
    )
    assert passed["conclusion"] == "passed"

    mutated = copy.deepcopy(evaluator_reports)
    mutated["summary"]["document_summary_faithfulness"] = 0.5
    with pytest.raises(ValueError, match="summary.*document_summary_faithfulness"):
        evaluate_gate(
            operations=operations,
            localization=localization,
            tag_quality=tag_quality,
            components=components,
            evaluator_reports=mutated,
            verification=verification,
        )

    with pytest.raises(ValueError, match="evaluator report"):
        evaluate_gate(
            operations=operations,
            localization=localization,
            tag_quality=tag_quality,
            components=components,
            evaluator_reports={},
            verification=verification,
        )


def test_batch_2_acceptance_gate_rejects_a_mutated_case_metric() -> None:
    path = ROOT / "scripts" / "check_topic5_batch_2_acceptance_gate.py"
    assert path.is_file(), f"missing acceptance gate: {path}"
    spec = importlib.util.spec_from_file_location("topic5_batch2_acceptance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    reports = {
        "metadata": _load_script("metadata_contract").build_report(),
        "summary": _load_script("summary_faithfulness").build_report(),
        "consistency": _load_script("artifact_consistency").build_report(),
        "entity": _load_script("entity_passthrough").build_report(),
        "topic11": _load_script("topic11_adapter").build_report(),
    }
    passed = module.evaluate_reports(reports)
    assert passed["passed"] is True

    mutated = copy.deepcopy(reports)
    mutated["consistency"]["tampering_detection_rate"] = 0.5
    with pytest.raises(ValueError, match="consistency.*tampering_detection_rate"):
        module.evaluate_reports(mutated)
