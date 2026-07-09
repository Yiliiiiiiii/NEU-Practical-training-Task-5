"""Validate mapping recall, badcase, required-missing, and split-gap gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "mapping_splits" / "summary.json"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _float(value: Any) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


def _int(value: Any) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    splits = report.get("splits")
    if isinstance(splits, list):
        return [row for row in splits if isinstance(row, dict)]
    summary = report.get("summary", {})
    if isinstance(summary, dict):
        return [
            {
                "split": "summary",
                "assisted_mapping_recall": summary.get(
                    "assisted_mapping_recall", summary.get("mapping_recall", 0.0)
                ),
                "badcase_violations": summary.get("badcase_violation_count", 0),
                "required_missing": summary.get(
                    "missing_gold_mappings",
                    summary.get("required_missing_count", 0),
                ),
                "package_pass_rate": summary.get("package_pass_rate", 0.0),
            }
        ]
    return []


def check_report(
    report: dict[str, Any],
    *,
    min_assisted_recall: float,
    max_badcase_violations: int,
    max_required_missing: int,
    max_dev_test_gap: float,
    max_test_blind_gap: float,
) -> dict[str, Any]:
    failures: list[str] = []
    rows = _rows(report)
    for row in rows:
        split = str(row.get("split", "summary"))
        assisted = _float(row.get("assisted_mapping_recall"))
        badcases = _int(row.get("badcase_violations"))
        required_missing = _int(row.get("required_missing"))
        if assisted < min_assisted_recall:
            failures.append(
                f"{split}: assisted recall {assisted:.3f} < {min_assisted_recall:.3f}"
            )
        if badcases > max_badcase_violations:
            failures.append(
                f"{split}: badcase violations {badcases} > {max_badcase_violations}"
            )
        if required_missing > max_required_missing:
            failures.append(
                f"{split}: required missing {required_missing} > {max_required_missing}"
            )

    gap = report.get("generalization_gap", {})
    if isinstance(gap, dict):
        dev_test = _float(gap.get("dev_vs_test_assisted_recall"))
        test_blind = _float(gap.get("test_vs_blind_assisted_recall"))
        if dev_test > max_dev_test_gap:
            failures.append(
                f"dev/test assisted recall gap {dev_test:.3f} > {max_dev_test_gap:.3f}"
            )
        if test_blind > max_test_blind_gap:
            failures.append(
                f"test/blind assisted recall gap {test_blind:.3f} > {max_test_blind_gap:.3f}"
            )

    return {
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--min-assisted-recall", type=float, default=0.85)
    parser.add_argument("--max-badcase-violations", type=int, default=0)
    parser.add_argument("--max-required-missing", type=int, default=0)
    parser.add_argument("--max-dev-test-gap", type=float, default=0.05)
    parser.add_argument("--max-test-blind-gap", type=float, default=0.05)
    args = parser.parse_args()

    result = check_report(
        _load_json(args.report),
        min_assisted_recall=args.min_assisted_recall,
        max_badcase_violations=args.max_badcase_violations,
        max_required_missing=args.max_required_missing,
        max_dev_test_gap=args.max_dev_test_gap,
        max_test_blind_gap=args.max_test_blind_gap,
    )
    if result["passed"]:
        print("mapping quality gate passed")
        return
    print("mapping quality gate failed")
    for failure in result["failures"]:
        print(f"- {failure}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
