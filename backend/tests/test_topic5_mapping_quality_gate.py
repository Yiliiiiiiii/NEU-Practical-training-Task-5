from __future__ import annotations

from scripts.check_topic5_mapping_quality_gate import build_gate_report


def report(auto_precision: float, auto_recall: float, *, review_rate: float = 0.0) -> dict:
    return {
        "status": "passed",
        "metrics": {
            "auto_precision": auto_precision,
            "auto_recall": auto_recall,
            "review_required_rate": review_rate,
            "required_missing": 0,
            "badcase_violations": 0,
        },
    }


def test_quality_gate_passes_when_all_thresholds_met() -> None:
    gate = build_gate_report(
        {
            "dev": report(0.95, 0.91),
            "test": report(0.94, 0.90),
            "blind": report(0.93, 0.88),
        },
        mode="global_assignment",
    )

    assert gate["status"] == "passed"
    assert gate["failed_checks"] == []
    assert gate["actual"]["test_vs_blind_gap"] == 0.02


def test_quality_gate_fails_on_split_gap_and_missing_required() -> None:
    blind = report(0.93, 0.80)
    blind["metrics"]["required_missing"] = 1

    gate = build_gate_report(
        {
            "dev": report(0.95, 0.91),
            "test": report(0.94, 0.90),
            "blind": blind,
        },
        mode="global_assignment",
    )

    assert gate["status"] == "failed"
    assert "blind_auto_recall_below_threshold" in gate["failed_checks"]
    assert "required_missing" in gate["failed_checks"]
    assert "test_vs_blind_gap_above_threshold" in gate["failed_checks"]
