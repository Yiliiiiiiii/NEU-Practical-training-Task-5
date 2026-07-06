import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "==":
        return actual == expected
    if op == ">=":
        return actual >= expected
    if op == "<=":
        return actual <= expected
    raise ValueError(f"unsupported gate operator: {op}")


def run(
    metrics_path: str | Path,
    gates_path: str | Path,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    metrics = read_json(metrics_path)
    gate_config = read_json(gates_path)
    results: list[dict[str, Any]] = []
    for gate in gate_config.get("gates", []):
        metric = str(gate["metric"])
        if metric not in metrics:
            results.append(
                {
                    "metric": metric,
                    "passed": False,
                    "actual": None,
                    "op": gate["op"],
                    "expected": gate["value"],
                    "reason": "metric_missing",
                }
            )
            continue
        actual = metrics[metric]
        passed = compare(actual, str(gate["op"]), gate["value"])
        results.append(
            {
                "metric": metric,
                "passed": passed,
                "actual": actual,
                "op": gate["op"],
                "expected": gate["value"],
                "reason": None if passed else "threshold_failed",
            }
        )
    failed = [item for item in results if not item["passed"]]
    report = {
        "passed": not failed,
        "gate_count": len(results),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "results": results,
    }
    if out_path is not None:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check SchemaPack regression gates.")
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--gates", required=True)
    parser.add_argument("--out")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(args.metrics, args.gates, args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
