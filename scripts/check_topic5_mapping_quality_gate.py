"""Run the Topic 5 mapping quality gate across dev/test/blind splits."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_topic5_standard_uir_mapping import (  # noqa: E402
    build_report,
    evaluate_dataset,
    load_dataset,
    render_markdown as render_eval_markdown,
    write_json,
    write_markdown,
)


DEFAULT_DATASET = ROOT / "eval" / "topic5_standard_uir"
DEFAULT_JSON = ROOT / "reports" / "topic5_mapping_quality_gate_report.json"
DEFAULT_MD = ROOT / "reports" / "topic5_mapping_quality_gate_report.md"
DEFAULT_THRESHOLDS = {
    "auto_precision": 0.90,
    "auto_recall": 0.85,
    "review_required_rate": 0.08,
    "test_vs_blind_gap": 0.03,
}


def build_gate_report(
    split_reports: dict[str, dict[str, Any]],
    *,
    mode: str,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    failed: list[str] = []
    actual: dict[str, Any] = {}
    for split in ("dev", "test", "blind"):
        metrics = split_reports[split]["metrics"]
        actual[split] = metrics
        if metrics["auto_precision"] < thresholds["auto_precision"]:
            failed.append(f"{split}_auto_precision_below_threshold")
        if metrics["auto_recall"] < thresholds["auto_recall"]:
            failed.append(f"{split}_auto_recall_below_threshold")
        if metrics["review_required_rate"] > thresholds["review_required_rate"]:
            failed.append(f"{split}_review_required_rate_above_threshold")
        if metrics["required_missing"]:
            failed.append("required_missing")
        if metrics["badcase_violations"]:
            failed.append("badcase_violations")

    gap = round(
        abs(
            split_reports["test"]["metrics"]["auto_recall"]
            - split_reports["blind"]["metrics"]["auto_recall"]
        ),
        4,
    )
    actual["test_vs_blind_gap"] = gap
    if gap > thresholds["test_vs_blind_gap"]:
        failed.append("test_vs_blind_gap_above_threshold")

    failed = sorted(set(failed))
    return {
        "status": "passed" if not failed else "failed",
        "mode": mode,
        "thresholds": thresholds,
        "actual": actual,
        "failed_checks": failed,
    }


def render_markdown(report: dict[str, Any]) -> str:
    actual = report["actual"]
    test_metrics = actual["test"]
    lines = [
        "# Topic 5 Mapping Quality Gate",
        "",
        f"- status: {report['status']}",
        f"- mode: {report['mode']}",
        f"- auto recall: {test_metrics['auto_recall']:.4f}",
        f"- auto precision: {test_metrics['auto_precision']:.4f}",
        f"- review-required rate: {test_metrics['review_required_rate']:.4f}",
        f"- required missing: {test_metrics['required_missing']}",
        f"- badcase violations: {test_metrics['badcase_violations']}",
        f"- test vs blind gap: {actual['test_vs_blind_gap']:.4f}",
        "",
        "## Split Metrics",
        "",
        "| Split | Auto precision | Auto recall | Review rate | Required missing | Badcases |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for split in ("dev", "test", "blind"):
        metrics = actual[split]
        lines.append(
            f"| {split} | {metrics['auto_precision']:.4f} | "
            f"{metrics['auto_recall']:.4f} | "
            f"{metrics['review_required_rate']:.4f} | "
            f"{metrics['required_missing']} | "
            f"{metrics['badcase_violations']} |"
        )
    lines.extend(["", "## Claim Boundary", ""])
    if report["status"] == "passed":
        lines.append(
            "The project can claim Topic 5 benchmark-level auto mapping recall >= 0.85 "
            "within the declared standard UIR benchmark scope."
        )
    else:
        lines.append(
            "The project must not claim auto mapping recall >= 0.85; it may claim "
            "benchmark infrastructure is ready and report the current measured value."
        )
    lines.append(
        "This is not a production shadow/blind claim unless "
        "production_shadow_eval_report.json is also completed."
    )
    if report["failed_checks"]:
        lines.extend(["", "## Failed Checks", ""])
        lines.extend(f"- {item}" for item in report["failed_checks"])
    return "\n".join(lines) + "\n"


def run_split_reports(
    *,
    dataset_root: Path,
    mode: str,
    thresholds: dict[str, float],
) -> dict[str, dict[str, Any]]:
    split_reports: dict[str, dict[str, Any]] = {}
    for split in ("dev", "test", "blind"):
        dataset = load_dataset(dataset_root, split)
        rows = evaluate_dataset(dataset, mapping_mode=mode)
        report = build_report(
            rows,
            split=split,
            thresholds={
                "auto_precision": thresholds["auto_precision"],
                "auto_recall": thresholds["auto_recall"],
                "review_required_rate": thresholds["review_required_rate"],
            },
        )
        report["mapping_mode"] = mode
        split_reports[split] = report
        write_json(ROOT / "reports" / f"topic5_standard_uir_{mode}_{split}.json", report)
        write_markdown(
            ROOT / "reports" / f"topic5_standard_uir_{mode}_{split}.md",
            render_eval_markdown(report),
        )
    return split_reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--mode", choices=["legacy", "global_assignment"], default="global_assignment")
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--fail-on-gate", action="store_true")
    args = parser.parse_args()

    split_reports = run_split_reports(
        dataset_root=args.dataset,
        mode=args.mode,
        thresholds=DEFAULT_THRESHOLDS,
    )
    report = build_gate_report(split_reports, mode=args.mode)
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report))
    if args.fail_on_gate and report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
