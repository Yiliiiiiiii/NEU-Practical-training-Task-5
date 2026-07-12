"""Measure Topic 5 stage scaling on frozen deterministic fixtures."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tracemalloc
from pathlib import Path
from typing import Any

from topic5_reliability_common import BACKEND, ROOT, canonical_json_bytes, load_json

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.schemas.topic5_execution import Topic5ExecutionOptions  # noqa: E402
from app.services.conversion_status_service import ConversionStatusService  # noqa: E402
from app.services.topic5_conversion_engine import (  # noqa: E402
    ConversionEngineContext,
    Topic5ConversionEngine,
)

DATASET = ROOT / "eval" / "topic5_performance" / "v1"
DEFAULT_OUTPUT = DATASET / "report.json"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _environment() -> dict[str, Any]:
    total_memory = None
    try:
        import psutil

        total_memory = psutil.virtual_memory().total
    except ImportError:
        pass
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor() or "unreported",
        "logical_cpu_count": os.cpu_count(),
        "total_memory_bytes": total_memory,
        "memory_measurement": "tracemalloc Python allocations",
    }


def _run_fixture(path: Path) -> dict[str, Any]:
    request = Topic5ConvertRequest.model_validate(load_json(path))
    options, warnings = Topic5ExecutionOptions.parse_legacy(request.options)
    tracemalloc.start()
    result = Topic5ConversionEngine().convert(
        uir=request.uir,
        target_schema=request.target_schema,
        metadata_template=request.metadata_template,
        mapping_rules=request.effective_mapping_template,
        content_organization=request.content_organization,
        execution_options=options,
        output_assertions=request.output_assertions,
        engine_context=ConversionEngineContext(
            task_id=f"performance-{path.stem}",
            doc_id=request.uir.doc_id,
            input_mode="performance_fixture",
            mapping_input_name=request.mapping_input_name,
            settings=Settings(),
            option_warnings=warnings,
        ),
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    artifact_bytes = len(
        canonical_json_bytes(
            {
                "content_json": result.rendered.structured_json,
                "content_markdown": result.rendered.markdown,
                "chunks": result.rendered.chunks,
            }
        )
    )
    return {
        "fixture": path.name,
        "block_count": len(request.uir.blocks),
        "candidate_count": len(result.candidates),
        "stage_durations_ms": result.stage_durations_ms,
        "total_duration_ms": result.stage_durations_ms["total"],
        "peak_memory_bytes": peak,
        "artifact_bytes": artifact_bytes,
        "chunk_count": len(result.rendered.chunks),
        "status": ConversionStatusService.determine(result.status_input),
        "passed": result.validation_report.passed
        and result.artifact_consistency_report.passed,
    }


def _measure_fixture(path: Path, repetitions: int) -> dict[str, Any]:
    attempts = [_run_fixture(path) for _index in range(repetitions)]
    first = attempts[0]
    stage_names = first["stage_durations_ms"]
    result = {
        **first,
        "stage_durations_ms": {
            stage: round(
                sum(item["stage_durations_ms"][stage] for item in attempts)
                / repetitions,
                3,
            )
            for stage in stage_names
        },
        "peak_memory_bytes": max(item["peak_memory_bytes"] for item in attempts),
        "passed": all(item["passed"] for item in attempts),
        "measurement_repetitions": repetitions,
        "attempt_total_durations_ms": [
            item["total_duration_ms"] for item in attempts
        ],
    }
    result["total_duration_ms"] = result["stage_durations_ms"]["total"]
    return result


def _baseline_checks(
    cases: list[dict[str, Any]], baseline_path: Path | None
) -> dict[str, Any]:
    if baseline_path is None:
        return {"status": "captured", "passed": True, "regressions": []}
    baseline = load_json(baseline_path)
    expected_repetitions = cases[0]["measurement_repetitions"]
    if baseline.get("measurement_repetitions") != expected_repetitions:
        return {
            "status": "compared",
            "baseline": str(baseline_path),
            "passed": False,
            "regressions": [
                {
                    "metric": "measurement_repetitions",
                    "baseline": baseline.get("measurement_repetitions"),
                    "actual": expected_repetitions,
                }
            ],
        }
    prior = {case["block_count"]: case for case in baseline["cases"]}
    regressions = []
    for case in cases:
        old = prior.get(case["block_count"])
        if old is None:
            regressions.append({"block_count": case["block_count"], "metric": "missing"})
            continue
        baseline_duration = float(old["total_duration_ms"])
        actual_duration = float(case["total_duration_ms"])
        allowed_duration = max(
            baseline_duration * 1.2,
            baseline_duration + 5.0,
        )
        if actual_duration > allowed_duration:
            regressions.append(
                {
                    "block_count": case["block_count"],
                    "metric": "total_duration_ms",
                    "baseline": old["total_duration_ms"],
                    "actual": actual_duration,
                    "allowed": allowed_duration,
                }
            )
        allowed_memory = int(float(old["peak_memory_bytes"]) * 1.25)
        if case["peak_memory_bytes"] > allowed_memory:
            regressions.append(
                {
                    "block_count": case["block_count"],
                    "metric": "peak_memory_bytes",
                    "baseline": old["peak_memory_bytes"],
                    "actual": case["peak_memory_bytes"],
                    "allowed": allowed_memory,
                }
            )
    return {
        "status": "compared",
        "baseline": str(baseline_path),
        "comparison_metrics": ["total_duration_ms", "peak_memory_bytes"],
        "stage_durations": "diagnostic_only",
        "passed": not regressions,
        "regressions": regressions,
    }


def _performance_checks(
    cases: list[dict[str, Any]], scaling: dict[str, Any]
) -> dict[str, bool]:
    return {
        "all_cases_completed": all(case["passed"] for case in cases),
        "linear_duration_scaling": not scaling["quadratic_blowup_detected"],
        "linear_memory_scaling": not scaling["memory_blowup_detected"],
    }


def run_evaluation(
    *, baseline_path: Path | None = None, repetitions: int = 2
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    manifest = load_json(DATASET / "manifest.json")
    cases = [
        _measure_fixture(DATASET / "fixtures" / item["path"], repetitions)
        for item in manifest["fixtures"]
    ]
    by_size = {case["block_count"]: case for case in cases}
    large_ratio = by_size[10_000]["total_duration_ms"] / max(
        by_size[1_000]["total_duration_ms"], 0.001
    )
    memory_ratio = by_size[10_000]["peak_memory_bytes"] / max(
        by_size[1_000]["peak_memory_bytes"], 1
    )
    scaling = {
        "declared_expectation": "approximately linear in block count",
        "size_ratio_1000_to_10000": 10.0,
        "duration_ratio_1000_to_10000": large_ratio,
        "quadratic_blowup_detected": large_ratio > 25.0,
        "memory_ratio_1000_to_10000": memory_ratio,
        "memory_blowup_detected": memory_ratio > 12.5,
    }
    baseline = _baseline_checks(cases, baseline_path)
    performance_checks = _performance_checks(cases, scaling)
    passed = all(performance_checks.values())
    return {
        "status": "passed" if passed else "failed",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "commit_sha": _git_head(),
        "environment": _environment(),
        "case_count": len(cases),
        "measurement_repetitions": repetitions,
        "passed_count": sum(case["passed"] for case in cases),
        "cases": cases,
        "scaling": scaling,
        "performance_checks": performance_checks,
        "baseline_comparison": baseline,
        "baseline_comparison_role": "diagnostic_only",
        "claim_boundary": "Measured on the recorded host; no absolute production SLO claim.",
        "reproduction_command": "python scripts/eval_topic5_performance.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    report = run_evaluation(
        baseline_path=args.baseline, repetitions=args.repetitions
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
