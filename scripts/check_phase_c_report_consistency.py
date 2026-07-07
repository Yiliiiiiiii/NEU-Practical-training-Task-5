"""Check Phase C report metric consistency across evaluator outputs."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_SEMANTIC = ROOT / "reports" / "semantic_mapping_quality_report.json"
DEFAULT_STRICT = ROOT / "reports" / "strict_validation_failure_analysis.json"
DEFAULT_JSON = ROOT / "reports" / "phase_c_report_consistency.json"
DEFAULT_MD = ROOT / "reports" / "phase_c_report_consistency.md"


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("summary", {})
    return value if isinstance(value, dict) else {}


def _metric(summary: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in summary:
            return summary[key]
    return None


def _same_non_null(values: list[Any]) -> bool:
    known = [value for value in values if value is not None]
    return len(set(known)) <= 1


def _difference(metric: str, reason: str, values: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric": metric,
        "reason": reason,
        "values": values,
    }


def check_reports(
    *,
    mapping_path: str | Path,
    semantic_path: str | Path,
    strict_path: str | Path,
) -> dict[str, Any]:
    mapping = _summary(read_json(mapping_path))
    semantic = _summary(read_json(semantic_path))
    strict = _summary(read_json(strict_path))
    metrics: dict[str, dict[str, Any]] = {
        "dataset_size": {
            "mapping": _metric(mapping, "dataset_size"),
            "semantic": _metric(semantic, "dataset_size"),
            "strict": _metric(strict, "dataset_size", "package_count"),
        },
        "strict_pass_count": {
            "mapping": _metric(mapping, "strict_pass_count"),
            "semantic": _metric(semantic, "strict_pass_count"),
            "strict": _metric(strict, "strict_pass_count", "validation_pass_count"),
        },
        "required_missing_count": {
            "mapping": _metric(mapping, "required_missing_count"),
            "semantic": _metric(semantic, "required_missing_count"),
            "strict": _metric(strict, "required_missing_count"),
        },
        "review_required_count": {
            "mapping": _metric(mapping, "review_required_count"),
            "semantic": _metric(semantic, "review_required_count"),
            "strict": _metric(strict, "review_required_count"),
        },
        "badcase_violations": {
            "mapping": _metric(mapping, "badcase_violation_count", "badcase_violations"),
            "semantic": _metric(semantic, "badcase_violations", "badcase_violation_count"),
            "strict": _metric(strict, "badcase_violations", "badcase_violation_count"),
        },
        "llm_auto_accepted_count": {
            "mapping": _metric(mapping, "llm_auto_accepted_count"),
            "semantic": _metric(semantic, "llm_auto_accepted_count"),
            "strict": _metric(strict, "llm_auto_accepted_count"),
        },
    }

    differences: list[dict[str, Any]] = []
    for metric, values in metrics.items():
        if not _same_non_null(list(values.values())):
            differences.append(_difference(metric, "value_mismatch", values))

    for metric in ("badcase_violations", "llm_auto_accepted_count"):
        values = metrics[metric]
        if any((value or 0) != 0 for value in values.values() if value is not None):
            differences.append(
                _difference(metric, "semantic_safety_gate_failed", values)
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": not differences,
        "differences": differences,
        "metrics": metrics,
        "inputs": {
            "mapping_path": str(mapping_path),
            "semantic_path": str(semantic_path),
            "strict_path": str(strict_path),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase C Report Consistency",
        "",
        f"- Passed: {report['passed']}",
        f"- Generated at: {report['generated_at']}",
        "",
        "## Metrics",
        "",
        "| Metric | Mapping | Semantic | Strict |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric, values in report["metrics"].items():
        lines.append(
            f"| {metric} | {values.get('mapping')} | "
            f"{values.get('semantic')} | {values.get('strict')} |"
        )
    lines.extend(["", "## Differences", ""])
    if report["differences"]:
        for item in report["differences"]:
            lines.append(
                f"- {item['metric']}: {item['reason']} "
                f"({json.dumps(item['values'], ensure_ascii=False, sort_keys=True)})"
            )
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def run(
    *,
    mapping_path: str | Path,
    semantic_path: str | Path,
    strict_path: str | Path,
    out_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    report = check_reports(
        mapping_path=mapping_path,
        semantic_path=semantic_path,
        strict_path=strict_path,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--semantic", type=Path, default=DEFAULT_SEMANTIC)
    parser.add_argument("--strict", type=Path, default=DEFAULT_STRICT)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        mapping_path=args.mapping,
        semantic_path=args.semantic,
        strict_path=args.strict,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
