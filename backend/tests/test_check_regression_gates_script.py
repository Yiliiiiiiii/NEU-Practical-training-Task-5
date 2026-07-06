import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_regression_gates  # noqa: E402


def test_regression_gate_passes_safe_metrics(tmp_path) -> None:
    metrics = tmp_path / "metrics.json"
    gates = tmp_path / "gates.json"
    out = tmp_path / "result.json"
    metrics.write_text(
        json.dumps(
            {
                "badcase_violation_count": 0,
                "llm_auto_accepted_count": 0,
                "package_verification_rate": 1.0,
                "adapter_trace_coverage": 1.0,
            }
        ),
        encoding="utf-8",
    )
    gates.write_text(
        json.dumps(
            {
                "gates": [
                    {"metric": "badcase_violation_count", "op": "==", "value": 0},
                    {"metric": "llm_auto_accepted_count", "op": "==", "value": 0},
                    {"metric": "package_verification_rate", "op": ">=", "value": 1.0},
                    {"metric": "adapter_trace_coverage", "op": ">=", "value": 0.95},
                ]
            }
        ),
        encoding="utf-8",
    )

    report = check_regression_gates.run(metrics, gates, out)

    assert report["passed"] is True
    assert report["failed_gate_count"] == 0
    assert out.is_file()


def test_regression_gate_fails_missing_or_unsafe_metrics(tmp_path) -> None:
    metrics = tmp_path / "metrics.json"
    gates = tmp_path / "gates.json"
    metrics.write_text('{"badcase_violation_count": 1}', encoding="utf-8")
    gates.write_text(
        '{"gates":[{"metric":"badcase_violation_count","op":"==","value":0},'
        '{"metric":"llm_auto_accepted_count","op":"==","value":0}]}',
        encoding="utf-8",
    )

    report = check_regression_gates.run(metrics, gates)

    assert report["passed"] is False
    assert report["failed_gate_count"] == 2
    assert {item["reason"] for item in report["failed_gates"]} == {
        "threshold_failed",
        "metric_missing",
    }
