import json
import sys
from pathlib import Path
from typing import Any

TOTAL_LINES = 95.0
TOTAL_BRANCHES = 90.0
CORE_FILE_LINES = 95.0
CORE_PREFIXES = (
    "app/api/v1/",
    "app/engines/",
    "app/services/",
    "app/validators/",
)


def _line_percent(summary: dict[str, Any]) -> float:
    statements = int(summary.get("num_statements", 0))
    if statements:
        return 100.0 * int(summary.get("covered_lines", 0)) / statements
    return float(summary.get("percent_covered", 100.0))


def _branch_percent(summary: dict[str, Any]) -> float:
    branches = int(summary.get("num_branches", 0))
    if not branches:
        return 100.0
    return 100.0 * int(summary.get("covered_branches", 0)) / branches


def evaluate_coverage(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    totals = report.get("totals", {})
    total_lines = _line_percent(totals)
    total_branches = _branch_percent(totals)

    if total_lines < TOTAL_LINES:
        failures.append(
            f"total line coverage {total_lines:.2f}% < {TOTAL_LINES:.2f}%"
        )
    if total_branches < TOTAL_BRANCHES:
        failures.append(
            f"total branch coverage {total_branches:.2f}% < {TOTAL_BRANCHES:.2f}%"
        )

    for raw_path, file_report in sorted(report.get("files", {}).items()):
        path = raw_path.replace("\\", "/")
        if path.endswith("/__init__.py") or not path.startswith(CORE_PREFIXES):
            continue
        line_percent = _line_percent(file_report.get("summary", {}))
        if line_percent < CORE_FILE_LINES:
            failures.append(
                f"core file {path} line coverage "
                f"{line_percent:.2f}% < {CORE_FILE_LINES:.2f}%"
            )
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python tests/coverage_gate.py <coverage.json>")
        return 2
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    failures = evaluate_coverage(report)
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print("Coverage gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
