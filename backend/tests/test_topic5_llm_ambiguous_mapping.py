from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module():
    path = ROOT / "scripts" / "eval_topic5_llm_ambiguous_mapping.py"
    spec = importlib.util.spec_from_file_location(
        "eval_topic5_llm_ambiguous_mapping", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ambiguous_mapping_llm_evidence_is_review_only_and_non_mutating() -> None:
    report = load_module().evaluate()
    metrics = report["metrics"]

    assert report["status"] == "passed"
    assert metrics["ambiguous_case_count"] >= 1
    assert metrics["llm_fallback_exercised_count"] == metrics["ambiguous_case_count"]
    assert metrics["review_required_count"] == metrics["ambiguous_case_count"]
    assert metrics["auto_accepted_count"] == 0
    assert metrics["confidence_bound_violations"] == 0
    assert metrics["missing_reason_count"] == 0
    assert metrics["missing_evidence_count"] == 0
    assert metrics["production_rule_catalog_unchanged"] is True
    assert metrics["network_used"] is False
    assert all(case["auto_accept_allowed"] is False for case in report["cases"])
