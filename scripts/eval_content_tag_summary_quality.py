"""Run content tag quality and summary faithfulness into one basic-stage report."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_content_tag_quality import run_evaluation as run_tag_evaluation
from eval_summary_faithfulness import run_evaluation as run_summary_evaluation


def build_report(tag_report: dict[str, Any], summary_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "tag_status": tag_report.get("status"),
        "summary_status": summary_report.get("status"),
        "sample_count": {
            "tag": tag_report.get("sample_count"),
            "summary": summary_report.get("sample_count"),
        },
        "tag_metrics": tag_report.get("metrics", {}),
        "summary_metrics": summary_report.get("metrics", {}),
        "summary_hallucination_count": summary_report.get("metrics", {}).get("hallucination_count", 0),
        "source_link_coverage": tag_report.get("metrics", {}).get("source_link_coverage"),
        "management_tag_rule_pass_rate": tag_report.get("metrics", {}).get("management_tag_f1"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Content Tag and Summary Quality",
            "",
            f"- Tag status: {report['tag_status']}",
            f"- Summary status: {report['summary_status']}",
            f"- Summary hallucination count: {report['summary_hallucination_count']}",
            f"- Source link coverage: {report['source_link_coverage']}",
            f"- Management tag rule pass rate: {report['management_tag_rule_pass_rate']}",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    tag_json = args.out_json.with_name("content_tag_quality_detail.json")
    tag_md = args.out_md.with_name("content_tag_quality_detail.md")
    summary_json = args.out_json.with_name("summary_faithfulness_detail.json")
    summary_md = args.out_md.with_name("summary_faithfulness_detail.md")
    tag_report = run_tag_evaluation(output_json=tag_json, output_md=tag_md)
    summary_report = run_summary_evaluation(output_json=summary_json, output_md=summary_md)
    report = build_report(tag_report, summary_report)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
