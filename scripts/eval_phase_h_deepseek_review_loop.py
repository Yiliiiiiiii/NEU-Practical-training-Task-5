"""Evaluate the Phase H DeepSeek proposal + simulated review loop safely."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "phase_h_deepseek_review_loop_report.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "phase_h_deepseek_review_loop_report.md"


def build_report(*, deepseek_configured: bool) -> dict[str, Any]:
    status = "configured_not_run" if deepseek_configured else "no_op"
    no_op_reason = None if deepseek_configured else "DeepSeek API key is not configured."
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "no_op_reason": no_op_reason,
        "deepseek_configured": deepseek_configured,
        "deepseek_requests": 0,
        "deepseek_candidates": 0,
        "evidence_linked_candidates": 0,
        "subagent_reviewed": 0,
        "subagent_approved": 0,
        "subagent_rejected": 0,
        "needs_human": 0,
        "applied_to_draft_pack": 0,
        "activated_after_gates": 0,
        "badcase_violations": 0,
        "llm_auto_accepted_count": 0,
        "secret_leaks": 0,
        "snapshot_mutations": 0,
        "measurable_recall_delta": 0.0,
        "strict_pass_delta": 0,
        "safety_policy": {
            "deepseek_may_only_propose_candidates": True,
            "llm_suggestions_require_review": True,
            "draft_pack_activation_requires_gates": True,
            "llm_auto_accept_forbidden": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase H DeepSeek Review Loop",
        "",
        f"- Status: {report['status']}",
        f"- DeepSeek configured: {report['deepseek_configured']}",
    ]
    if report.get("no_op_reason"):
        lines.append(f"- No-op reason: {report['no_op_reason']}")
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key in (
        "deepseek_requests",
        "deepseek_candidates",
        "evidence_linked_candidates",
        "subagent_reviewed",
        "subagent_approved",
        "subagent_rejected",
        "needs_human",
        "applied_to_draft_pack",
        "activated_after_gates",
        "badcase_violations",
        "llm_auto_accepted_count",
        "secret_leaks",
        "snapshot_mutations",
        "measurable_recall_delta",
        "strict_pass_delta",
    ):
        lines.append(f"| {key} | {report[key]} |")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "DeepSeek candidates are proposals only. This report never writes accepted mappings or activates knowledge packs.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], out: Path, markdown: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--deepseek-api-key", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    key = args.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY")
    report = build_report(deepseek_configured=bool(key))
    write_report(report, args.out, args.markdown)
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
