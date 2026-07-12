from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_calibration_is_frozen_from_dev_and_pinned_to_engine_commit() -> None:
    calibration = json.loads(
        (ROOT / "eval" / "topic5_mapping_engine_v2" / "calibration.json").read_text(
            encoding="utf-8"
        )
    )

    assert calibration["fit_split"] == "dev"
    assert calibration["test_labels_used_for_fit"] is False
    assert calibration["fit_engine_commit"] == "e2101d0d0cc95235585fc7c2fdd25a0767e19234"
    assert calibration["thresholds"] == {
        "auto_accept": 1.0,
        "review_required": 0.5,
    }
    assert calibration["brier_score"] == 0.0
    assert calibration["expected_calibration_error"] == 0.0


def test_calibration_builder_reproduces_frozen_artifact() -> None:
    fitter = _load_script("fit_topic5_mapping_v2_calibration.py")
    frozen = json.loads(
        (ROOT / "eval" / "topic5_mapping_engine_v2" / "calibration.json").read_text(
            encoding="utf-8"
        )
    )

    rebuilt = fitter.build_artifact(
        ROOT / "eval" / "topic5_mapping_v2",
        engine_commit=frozen["fit_engine_commit"],
    )

    assert rebuilt == frozen


def test_mapping_v2_gate_consumes_reports_and_meets_public_targets() -> None:
    gate = _load_script("check_topic5_mapping_v2_gate.py")

    report = gate.check(ROOT / "eval" / "topic5_mapping_engine_v2")

    assert report["status"] == "passed"
    assert report["failures"] == []
    assert report["test_metrics"]["auto_exact_field_accuracy"] >= 0.85
    assert report["test_metrics"]["auto_precision"] >= 0.90
    assert report["test_metrics"]["auto_recall"] >= 0.85
    assert report["test_metrics"]["auto_f1"] >= 0.87
    assert report["test_metrics"]["schema_held_out_f1"] >= 0.82
    assert report["external_blind_status"] == "not_run"
    assert report["can_claim_production_blind_0_85"] is False


def test_mapping_v2_reports_use_global_assignment_and_calibration() -> None:
    for split in ("dev", "test"):
        report = json.loads(
            (
                ROOT
                / "eval"
                / "topic5_mapping_engine_v2"
                / "reports"
                / f"{split}.json"
            ).read_text(encoding="utf-8")
        )
        assert report["status"] == "passed"
        assert report["engine"]["mapping_mode"] == "global_assignment"
        assert report["engine"]["assignment_algorithm"] == (
            "maximum_weight_bipartite"
        )
        assert report["engine"]["calibration_fit_split"] == "dev"
        assert report["engine"]["llm_fallback"] is False
