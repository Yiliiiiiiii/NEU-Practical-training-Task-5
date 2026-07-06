"""Build the static Evaluation Center scorecard from metrics and gate definitions."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.evaluation_center_service import SCORECARD_METRICS  # noqa: E402


WARNINGS = [
    (
        "Package verification does not imply every target field passes "
        "strict semantic validation."
    ),
    "LLM suggestions and Schema Drafts never activate production rules automatically.",
    (
        "Lineage proves traceability and decision history; it does not by itself "
        "prove strict semantic correctness."
    ),
]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def metric_card(config: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    metric_id = str(config["metric_id"])
    value = metrics.get(metric_id)
    target = config["target"]
    passed = False
    if isinstance(value, int | float) and isinstance(target, int | float):
        passed = value <= target if config["direction"] == "lower" else value >= target
    status = (
        "passed"
        if passed
        else "failed"
        if config["hard_gate"] and value is not None
        else "needs_attention"
    )
    return {
        "metric_id": metric_id,
        "name": config["name"],
        "value": value,
        "target": target,
        "status": status,
        "explanation": config["explanation"],
    }


def evaluate_gate(gate: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    metric = str(gate["metric"])
    operator = str(gate["op"])
    expected = gate["value"]
    actual = metrics.get(metric)
    comparisons = {
        "==": lambda left, right: left == right,
        ">=": lambda left, right: left >= right,
        "<=": lambda left, right: left <= right,
        ">": lambda left, right: left > right,
        "<": lambda left, right: left < right,
    }
    passed = (
        actual is not None
        and operator in comparisons
        and comparisons[operator](actual, expected)
    )
    return {
        "metric": metric,
        "op": operator,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "reason": None if passed else f"{metric} {actual!r} does not satisfy {operator} {expected!r}",
    }


def build_scorecard(
    metrics: dict[str, Any],
    gate_payload: dict[str, Any],
) -> dict[str, Any]:
    gates = [
        evaluate_gate(gate, metrics)
        for gate in gate_payload.get("gates", [])
        if isinstance(gate, dict)
    ]
    passed_count = sum(1 for gate in gates if gate["passed"])
    return {
        "summary": {
            "status": "passed" if passed_count == len(gates) else "failed",
            "generated_at": datetime.now(UTC).isoformat(),
            "gates_passed": passed_count,
            "gates_total": len(gates),
        },
        "metrics": metrics,
        "cards": [metric_card(config, metrics) for config in SCORECARD_METRICS],
        "regression_gates": gates,
        "warnings": WARNINGS,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    metrics = report["metrics"]
    lines = [
        "# Evaluation Center Scorecard",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Overall status | {summary['status']} |",
        f"| Gates | {summary['gates_passed']}/{summary['gates_total']} |",
        f"| Package verification | {metrics.get('package_verification_rate', 'not reported')} |",
        f"| Badcase violations | {metrics.get('badcase_violation_count', 'not reported')} |",
        f"| LLM auto accepted | {metrics.get('llm_auto_accepted_count', 'not reported')} |",
        "",
        "## Metrics",
        "",
        "| Metric | Current | Target | Status | Note |",
        "|---|---:|---:|---|---|",
    ]
    lines.extend(
        (
            f"| {card['name']} | {card['value'] if card['value'] is not None else 'not reported'} "
            f"| {card['target']} | {card['status']} | {card['explanation']} |"
        )
        for card in report["cards"]
    )
    lines.extend(
        [
            "",
            "## Regression Gates",
            "",
            "| Gate | Current | Target | Status |",
            "|---|---:|---:|---|",
        ]
    )
    lines.extend(
        (
            f"| {gate['metric']} | {gate['actual']} | "
            f"{gate['op']} {gate['expected']} | "
            f"{'passed' if gate['passed'] else 'failed'} |"
        )
        for gate in report["regression_gates"]
    )
    lines.extend(
        [
            "",
            "## Known Gaps",
            "",
            "- Package verification is not semantic strict validation.",
            "- Meeting and policy fields may still require human review.",
            "",
            "## Reproduction",
            "",
            "```powershell",
            "backend\\.venv\\Scripts\\python.exe scripts\\build_evaluation_center_scorecard.py `",
            "  --metrics reports\\evaluation_center\\current_metrics.json `",
            "  --gates reports\\evaluation_center\\regression_gates.json `",
            "  --out reports\\evaluation_center\\scorecard.json `",
            "  --markdown reports\\evaluation_center\\scorecard.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def run(
    *,
    metrics_path: str | Path,
    gates_path: str | Path,
    out_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    report = build_scorecard(
        read_json(Path(metrics_path)),
        read_json(Path(gates_path)),
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--gates", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        metrics_path=args.metrics,
        gates_path=args.gates,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
