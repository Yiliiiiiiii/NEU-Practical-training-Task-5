import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "eval_non_procurement_mapping.py"


def load_module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "eval_non_procurement_mapping",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_report_uses_required_contract_and_baseline_delta() -> None:
    module = load_module()
    items = [
        {
            "doc_id": "g1",
            "doc_type": "general_doc",
            "schema_id": "general_doc",
            "template_id": "general_doc_base_v1",
            "strict_passed": True,
            "package_passed": True,
            "required_missing": [],
            "review_evidence": [],
            "high_risk_auto_accepted": [],
            "metrics": {
                "mapping_recall": 0.75,
                "auto_mapping_recall": 0.5,
                "assisted_mapping_recall": 0.75,
                "review_required_rate": 0.25,
                "gold_signal_count": 4,
                "gold_mapping_count": 4,
                "auto_accepted_correct": 2,
                "review_required_correct": 1,
                "accepted_item_count": 3,
                "review_required_item_count": 1,
                "badcase_violation_count": 0,
            },
            "mapped_or_review_targets": ["title", "content"],
        }
    ]
    baseline = {
        "average_recall": 0.349,
        "review_required_count": 145,
        "required_missing_count": 18,
        "strict_pass_count": 4,
    }

    report = module.build_evaluation_report(items, baseline)

    assert report["summary"]["dataset_size"] == 1
    assert report["summary"]["strict_pass_count"] == 1
    assert report["summary"]["average_recall"] == 0.75
    assert report["summary"]["auto_mapping_recall"] == 0.5
    assert report["summary"]["assisted_mapping_recall"] == 0.75
    assert report["summary"]["review_required_rate"] == 0.25
    assert report["summary"]["package_verify_pass_count"] == 1
    assert report["delta"]["average_recall"] == 0.401
    assert set(report) >= {
        "by_doc_type",
        "by_field",
        "typical_improvements",
        "remaining_gaps",
        "failed_cases",
    }
    markdown = module.render_markdown(report)
    for heading in (
        "## Summary",
        "## Metrics By Document Type",
        "## Field-level Recall",
        "## Strict Validation",
        "## Review-required Analysis",
        "## Required Missing Analysis",
        "## Badcase Safety",
        "## Typical Improvements",
        "## Remaining Gaps",
        "## Commands",
    ):
        assert heading in markdown
