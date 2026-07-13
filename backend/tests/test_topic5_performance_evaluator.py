from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_module():
    path = ROOT / "scripts" / "eval_topic5_performance.py"
    scripts = str(path.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("eval_topic5_performance", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _case(duration: float) -> dict:
    return {
        "block_count": 1_000,
        "measurement_repetitions": 2,
        "stage_durations_ms": {"canonical": duration},
        "peak_memory_bytes": 1_000,
    }


def test_baseline_comparison_allows_five_milliseconds_of_timing_noise(
    tmp_path: Path,
) -> None:
    module = load_module()
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "measurement_repetitions": 2,
                "cases": [_case(12.0)],
            }
        ),
        encoding="utf-8",
    )

    assert module._baseline_checks([_case(16.9)], baseline_path)["passed"] is True
    failed = module._baseline_checks([_case(17.1)], baseline_path)
    assert failed["passed"] is False
    assert failed["regressions"][0]["allowed"] == 17.0
