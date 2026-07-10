from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from scripts.check_topic5_hard_gap_batch_1_gate import evaluate_gate
from scripts.eval_topic5_field_operations import build_report as field_report
from scripts.eval_topic5_field_operations import load_fixture as load_field_fixture
from scripts.eval_topic5_schema_localization import (
    build_report as localization_report,
)
from scripts.eval_topic5_schema_localization import (
    load_fixture as load_localization_fixture,
)

ROOT = Path(__file__).resolve().parents[2]


def test_field_operation_evaluator_has_fixed_110_case_denominator() -> None:
    report = field_report()

    assert report["case_count"] == 110
    assert report["field_operation_accuracy"] >= 0.95
    assert report["rename_accuracy"] >= 0.95
    assert report["merge_accuracy"] >= 0.95
    assert report["split_accuracy"] >= 0.95
    assert report["unsafe_operation_count"] == 0


def test_schema_localization_evaluator_has_fixed_40_case_denominator() -> None:
    report = localization_report()

    assert report["case_count"] == 40
    assert report["schema_localization_rate"] == 1.0
    assert report["error_code_accuracy"] == 1.0
    assert report["stage_accuracy"] == 1.0


def test_field_fixture_rejects_reduced_category_denominator(tmp_path: Path) -> None:
    source = ROOT / "eval" / "topic5_field_operations" / "v1" / "cases.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["groups"][0]["variants"].pop()
    path = tmp_path / "reduced.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="requires 20 rename cases"):
        load_field_fixture(path)


def test_localization_fixture_rejects_reduced_denominator(tmp_path: Path) -> None:
    source = ROOT / "eval" / "topic5_schema_localization" / "v1" / "cases.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["cases"].pop()
    path = tmp_path / "reduced.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="at least 40 cases"):
        load_localization_fixture(path)


def test_gate_passes_all_thresholds_and_fails_mutated_metric() -> None:
    operations = field_report()
    localization = localization_report()
    tag_quality = json.loads(
        (
            ROOT
            / "docs"
            / "交接"
            / "evidence"
            / "hard_gap_batch_1"
            / "tags"
            / "content_tag_quality.json"
        ).read_text(encoding="utf-8")
    )
    components = {
        name: {"passed": True}
        for name in ("metadata", "summary", "consistency", "entity", "topic11", "legacy")
    }
    verification = {
        "full_backend_tests_passed": True,
        "ruff_clean": True,
        "frontend_tests_passed": True,
        "openapi_export_passed": True,
    }

    passed = evaluate_gate(
        operations=operations,
        localization=localization,
        tag_quality=tag_quality,
        components=components,
        verification=verification,
    )
    assert passed["conclusion"] == "passed"

    failed_operations = copy.deepcopy(operations)
    failed_operations["merge_accuracy"] = 0.94
    failed = evaluate_gate(
        operations=failed_operations,
        localization=localization,
        tag_quality=tag_quality,
        components=components,
        verification=verification,
    )
    assert failed["conclusion"] == "failed"
    assert failed["failed_conditions"] == ["merge_accuracy"]
