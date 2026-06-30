import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"


def load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_build_report_aggregates_non_procurement_document_outcomes() -> None:
    evaluator = load_script("eval_non_procurement_doc")

    report = evaluator.build_report(
        [
            {
                "doc_id": "general-1",
                "doc_type": "general_doc",
                "catalog_key": "general_doc",
                "strict_passed": True,
                "required_missing": [],
                "review_evidence": [{"target_field": "summary"}],
                "high_risk_auto_accepted": [],
                "mapped_or_review_targets": ["title", "content"],
                "package_passed": True,
                "metrics": {
                    "mapping_recall": 1.0,
                    "missing_gold_mappings": 0,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                },
            },
            {
                "doc_id": "policy-1",
                "doc_type": "policy_doc",
                "catalog_key": "policy_doc",
                "strict_passed": False,
                "required_missing": ["publish_date", "issuing_authority"],
                "review_evidence": [],
                "high_risk_auto_accepted": [{"target_field": "effective_date"}],
                "package_passed": False,
                "metrics": {
                    "mapping_recall": 0.5,
                    "missing_gold_mappings": 2,
                    "badcase_violation_count": 1,
                    "badcase_violations": [{"case_id": "badcase-policy-date"}],
                },
                "errors": ["HTTPStatusError: validation report unavailable"],
            },
        ]
    )

    assert report["thresholds"] == {
        "general_doc": 2,
        "meeting_doc": 2,
        "policy_doc": 3,
        "mapping_recall": 0.65,
    }
    assert report["summary"]["document_count"] == 2
    assert report["summary"]["strict_pass_count"] == 1
    assert report["summary"]["strict_pass_rate"] == 0.5
    assert report["summary"]["required_missing_count"] == 2
    assert report["summary"]["mapping_recall_average"] == pytest.approx(0.75)
    assert report["summary"]["review_required_count"] == 1
    assert report["summary"]["high_risk_auto_accepted_count"] == 1
    assert report["summary"]["badcase_violation_count"] == 1
    assert report["summary"]["package_valid_count"] == 1
    assert report["by_doc_type"]["general_doc"]["strict_pass_count"] == 1
    assert report["by_doc_type"]["meeting_doc"]["document_count"] == 0
    assert report["by_doc_type"]["policy_doc"]["required_missing_count"] == 2
    assert report["failures"][0]["doc_id"] == "policy-1"
    assert report["failures"][0]["doc_type"] == "policy_doc"
    assert set(report["failures"][0]["reasons"]) >= {
        "strict_pass_failed",
        "missing_required_fields",
        "high_risk_auto_accepted",
        "badcase_violation",
        "package_invalid",
    }
    assert report["errors"] == [
        {
            "doc_id": "policy-1",
            "doc_type": "policy_doc",
            "message": "HTTPStatusError: validation report unavailable",
        }
    ]
    assert [item["doc_id"] for item in report["documents"]] == ["general-1", "policy-1"]
    assert report["documents"][0]["catalog"] == {
        "schema_id": "general_doc",
        "template_id": "general_doc_base_v1",
    }
    assert report["documents"][1]["failure_reasons"]


def test_non_procurement_rows_exclude_procurement_and_attach_catalogs() -> None:
    evaluator = load_script("eval_non_procurement_doc")
    rows: list[dict[str, Any]] = [
        {"doc_id": "general-1", "doc_type": "general_doc"},
        {"doc_id": "procurement-1", "doc_type": "procurement_doc"},
        {"doc_id": "meeting-1", "doc_type": "meeting_doc"},
        {"doc_id": "policy-1", "doc_type": "policy_doc"},
    ]

    selected = evaluator.non_procurement_rows(rows)

    assert [row["doc_id"] for row in selected] == [
        "general-1",
        "meeting-1",
        "policy-1",
    ]
    assert [(row["schema_id"], row["template_id"]) for row in selected] == [
        ("general_doc", "general_doc_base_v1"),
        ("meeting_doc", "meeting_doc_base_v1"),
        ("policy_doc", "policy_doc_base_v1"),
    ]


def test_render_markdown_includes_thresholds_failures_and_zero_count_types() -> None:
    evaluator = load_script("eval_non_procurement_doc")
    report = evaluator.build_report(
        [
            {
                "doc_id": "meeting-1",
                "doc_type": "meeting_doc",
                "catalog_key": "meeting_doc",
                "strict_passed": False,
                "required_missing": ["decisions"],
                "review_evidence": [],
                "high_risk_auto_accepted": [],
                "package_passed": True,
                "metrics": {
                    "mapping_recall": 0.4,
                    "missing_gold_mappings": 1,
                    "badcase_violation_count": 0,
                    "badcase_violations": [],
                },
            }
        ]
    )

    markdown = evaluator.render_markdown(report)

    assert "# Non-procurement Document Evaluation" in markdown
    assert "## Thresholds" in markdown
    assert "| general_doc | 0 |" in markdown
    assert "| meeting_doc | 1 |" in markdown
    assert "| policy_doc | 0 |" in markdown
    assert "## Failures" in markdown
    assert "meeting-1" in markdown


def test_build_report_derives_strict_pass_from_facts_and_defaults_risk_lists() -> None:
    evaluator = load_script("eval_non_procurement_doc")

    report = evaluator.build_report(
        [
            {
                "doc_id": "stale-pass",
                "doc_type": "general_doc",
                "strict_passed": True,
                "required_missing": ["content"],
                "package_passed": False,
                "metrics": {
                    "mapping_recall": 0.0,
                    "badcase_violation_count": 1,
                },
                "error": "boom",
            }
        ]
    )

    assert report["summary"]["strict_pass_count"] == 0
    assert report["documents"][0]["strict_passed"] is False
    assert report["documents"][0]["high_risk_auto_accepted"] == []
    assert set(report["documents"][0]["failure_reasons"]) >= {
        "evaluation_error",
        "missing_required_fields",
        "mapping_recall_below_threshold",
        "badcase_violation",
        "package_invalid",
        "mapped_or_review_targets_below_threshold",
    }
