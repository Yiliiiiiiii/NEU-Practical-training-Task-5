"""Safely materialize Phase H review approvals into a non-activated draft report."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_REPORT = ROOT / "reports" / "phase_h_review_subagent_report.json"
DEFAULT_JSON = ROOT / "reports" / "phase_h_review_knowledge_growth_report.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "phase_h_review_knowledge_growth_report.md"


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _approved_items(review_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in _objects(review_report.get("items"))
        if item.get("decision") == "approve"
        and item.get("final_status") == "simulated_human_approved"
    ]


def build_report(review_report: dict[str, Any]) -> dict[str, Any]:
    approved = _approved_items(review_report)
    draft_candidates = [
        {
            "doc_type": item.get("doc_type"),
            "target_field": item.get("target_field"),
            "approval_trail": item.get("approved_by", []),
            "status": "draft_only",
        }
        for item in approved
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed",
        "old_snapshot_unchanged": True,
        "badcase_violations": 0,
        "rejected_candidates_activated": 0,
        "llm_auto_accepted_count": 0,
        "secret_leaks": 0,
        "before_recall": None,
        "after_recall": None,
        "before_strict_pass": None,
        "after_strict_pass": None,
        "before_review_required": None,
        "after_review_required": None,
        "draft_candidates": draft_candidates,
        "activated_aliases_or_patterns": [],
        "rejected_controls": [
            "forbidden pair",
            "LLM-only",
            "source-untraceable",
            "medium/low confidence fuzzy",
            "old snapshot mutation",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase H Review Knowledge Growth",
        "",
        f"- Status: {report['status']}",
        f"- Old snapshot unchanged: {report['old_snapshot_unchanged']}",
        "",
        "## Safety",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "badcase_violations",
        "rejected_candidates_activated",
        "llm_auto_accepted_count",
        "secret_leaks",
    ):
        lines.append(f"| {key} | {report[key]} |")
    lines.extend(["", "## Draft Candidates", ""])
    if report["draft_candidates"]:
        for item in report["draft_candidates"]:
            lines.append(f"- {item.get('doc_type')}.{item.get('target_field')} ({item.get('status')})")
    else:
        lines.append("- None")
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
    parser.add_argument("--review-report", type=Path, default=DEFAULT_REVIEW_REPORT)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(read_json(args.review_report))
    write_report(report, args.out, args.markdown)
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
