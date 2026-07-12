"""Check frozen mapping-v2 engine, calibration, and public test evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "eval" / "topic5_mapping_engine_v2"

MINIMUMS = {
    "auto_exact_field_accuracy": 0.85,
    "auto_precision": 0.90,
    "auto_recall": 0.85,
    "auto_f1": 0.87,
    "macro_f1_by_schema": 0.82,
    "required_present_field_recall": 0.95,
}
ZERO_VIOLATIONS = {
    "negative_pair_violation_count",
    "duplicate_source_violation_count",
    "invalid_cardinality_count",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root: Path) -> dict[str, Any]:
    calibration_path = root / "calibration.json"
    dev_path = root / "reports" / "dev.json"
    test_path = root / "reports" / "test.json"
    calibration = _load(calibration_path)
    dev = _load(dev_path)
    test = _load(test_path)
    failures: list[str] = []

    if calibration.get("fit_split") != "dev":
        failures.append("calibration_fit_split")
    if calibration.get("test_labels_used_for_fit") is not False:
        failures.append("calibration_test_boundary")
    if calibration.get("fit_engine_commit") != dev.get("commit_sha"):
        failures.append("dev_engine_identity")
    if dev.get("commit_sha") != test.get("commit_sha"):
        failures.append("test_engine_identity")
    if dev.get("dataset", {}).get("sha256") != calibration.get("dataset_sha256"):
        failures.append("dev_dataset_identity")
    if test.get("dataset", {}).get("sha256") != calibration.get("dataset_sha256"):
        failures.append("test_dataset_identity")
    if calibration.get("method") != "bin_monotonic":
        failures.append("calibration_method")
    if not calibration.get("reliability_bins"):
        failures.append("reliability_bins")
    if not calibration.get("precision_coverage_curve"):
        failures.append("precision_coverage_curve")

    for split, report in (("dev", dev), ("test", test)):
        if report.get("status") != "passed":
            failures.append(f"{split}_status")
        engine = report.get("engine", {})
        if engine.get("assignment_algorithm") != "maximum_weight_bipartite":
            failures.append(f"{split}_assignment_algorithm")
        if engine.get("calibration_fit_split") != "dev":
            failures.append(f"{split}_calibration_boundary")

    metrics = test.get("metrics", {})
    for name, minimum in MINIMUMS.items():
        if float(metrics.get(name, -1.0)) < minimum:
            failures.append(name)
    for name in ZERO_VIOLATIONS:
        if metrics.get(name) != 0:
            failures.append(name)
    if float(metrics.get("review_required_rate", 1.0)) > 0.20:
        failures.append("review_required_rate")
    if float(metrics.get("schema_held_out_f1", 0.0)) < 0.82:
        failures.append("schema_held_out_f1")

    return {
        "status": "passed" if not failures else "failed",
        "failures": sorted(set(failures)),
        "engine_commit": calibration.get("fit_engine_commit"),
        "dataset_sha256": calibration.get("dataset_sha256"),
        "calibration_sha256": _sha256(calibration_path),
        "dev_report_sha256": _sha256(dev_path),
        "test_report_sha256": _sha256(test_path),
        "test_metrics": metrics,
        "external_blind_status": test.get("external_blind", {}).get("status"),
        "can_claim_production_blind_0_85": False,
        "claim_boundary": "frozen_public_mapping_v2_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.root.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
