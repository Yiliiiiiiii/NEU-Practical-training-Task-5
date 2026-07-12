from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    path = ROOT / "scripts" / "eval_topic5_performance.py"
    scripts = str(path.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("test_topic5_performance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_baseline_comparison_uses_end_to_end_duration_and_memory(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "measurement_repetitions": 2,
                "cases": [
                    {
                        "block_count": 1000,
                        "total_duration_ms": 100.0,
                        "peak_memory_bytes": 1_000,
                        "stage_durations_ms": {
                            "chunk": 50.0,
                            "verification": 10.0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    case = {
        "block_count": 1000,
        "measurement_repetitions": 2,
        "total_duration_ms": 119.0,
        "peak_memory_bytes": 1_200,
        "stage_durations_ms": {"chunk": 80.0, "verification": 30.0},
    }

    comparison = _load()._baseline_checks([case], baseline_path)

    assert comparison["passed"] is True
    assert comparison["comparison_metrics"] == [
        "total_duration_ms",
        "peak_memory_bytes",
    ]
    assert comparison["stage_durations"] == "diagnostic_only"


def test_baseline_comparison_rejects_end_to_end_regression(tmp_path: Path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "measurement_repetitions": 2,
                "cases": [
                    {
                        "block_count": 1000,
                        "total_duration_ms": 100.0,
                        "peak_memory_bytes": 1_000,
                        "stage_durations_ms": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    case = {
        "block_count": 1000,
        "measurement_repetitions": 2,
        "total_duration_ms": 121.0,
        "peak_memory_bytes": 1_000,
        "stage_durations_ms": {},
    }

    comparison = _load()._baseline_checks([case], baseline_path)

    assert comparison["passed"] is False
    assert comparison["regressions"] == [
        {
            "block_count": 1000,
            "metric": "total_duration_ms",
            "baseline": 100.0,
            "actual": 121.0,
            "allowed": 120.0,
        }
    ]


def test_performance_evidence_requires_linear_time_and_memory_scaling() -> None:
    checks = _load()._performance_checks(
        [{"passed": True}, {"passed": True}],
        {
            "quadratic_blowup_detected": False,
            "memory_blowup_detected": False,
        },
    )

    assert checks == {
        "all_cases_completed": True,
        "linear_duration_scaling": True,
        "linear_memory_scaling": True,
    }
