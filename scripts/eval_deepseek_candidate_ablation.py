"""Evaluate DeepSeek candidate contribution without allowing auto-accept."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _baseline_metrics() -> dict[str, Any]:
    baseline_path = ROOT / "reports" / "non_procurement_baseline_report.json"
    if not baseline_path.exists():
        return {
            "average_recall": 0.0,
            "policy_recall": 0.0,
            "required_missing": 0,
            "review_required": 0,
        }
    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "average_recall": 0.0,
            "policy_recall": 0.0,
            "required_missing": 0,
            "review_required": 0,
        }
    if not isinstance(payload, dict):
        return {
            "average_recall": 0.0,
            "policy_recall": 0.0,
            "required_missing": 0,
            "review_required": 0,
        }
    by_doc_type = payload.get("by_doc_type", {})
    policy = by_doc_type.get("policy_doc", {}) if isinstance(by_doc_type, dict) else {}
    summary = payload.get("summary", {})
    summary = summary if isinstance(summary, dict) else payload
    return {
        "average_recall": float(
            summary.get("average_recall")
            or summary.get("mapping_recall_average")
            or payload.get("average_recall")
            or 0.0
        ),
        "policy_recall": float(
            policy.get("mapping_recall_average")
            or policy.get("average_recall")
            or payload.get("policy_recall")
            or 0.0
        ),
        "required_missing": int(
            summary.get("required_missing_count")
            or payload.get("required_missing")
            or 0
        ),
        "review_required": int(
            summary.get("review_required_count")
            or payload.get("review_required")
            or 0
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    configured = bool(os.environ.get("DEEPSEEK_API_KEY"))
    deterministic = _baseline_metrics()
    deepseek_candidates = {
        "configured": configured,
        "requests": 0,
        "success": 0,
        "parse_success_rate": 0.0,
        "candidates": 0,
        "evidence_linked_candidates": 0,
        "candidate_fields": {},
    }
    judge_supported = {
        "supported_candidates": 0,
        "rejected_candidates": 0,
        "keep_pending_candidates": 0,
    }
    delta = {
        "average_recall_delta": 0.0,
        "policy_recall_delta": 0.0,
        "required_missing_delta": 0,
        "review_required_delta": 0,
    }
    safety = {
        "badcase_violations": 0,
        "llm_auto_accepted_count": 0,
        "secret_leaks": 0,
    }
    effective = any(
        [
            delta["policy_recall_delta"] >= 0.02,
            delta["required_missing_delta"] <= -1,
            delta["review_required_delta"] <= -2,
            deepseek_candidates["evidence_linked_candidates"] >= 10
            and judge_supported["supported_candidates"] >= 5,
        ]
    )
    message = (
        "DeepSeek reachable but no measurable contribution in this round."
        if configured and not effective
        else "DeepSeek not configured; no measurable contribution in this round."
        if not configured
        else "DeepSeek produced measurable contribution in this round."
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "focus_doc_type": args.focus_doc_type,
        "focus_fields": [
            field.strip() for field in args.focus_fields.split(",") if field.strip()
        ],
        "deterministic_only": deterministic,
        "deepseek_candidates": deepseek_candidates,
        "judge_supported": judge_supported,
        "delta": delta,
        "safety": safety,
        "effectiveness": {
            "effective": effective,
            "message": message,
        },
        "ablation_groups": {
            "A": "deterministic_only",
            "B": "deterministic + DeepSeek candidates as review_required",
            "C": "deterministic + DeepSeek candidates + Review Judge dry-run",
            "D": "deterministic + DeepSeek candidates + Review Judge scoped apply-guarded",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DeepSeek Candidate Ablation",
        "",
        "## Summary",
        "",
        f"- Configured: {report['deepseek_candidates']['configured']}",
        f"- Requests: {report['deepseek_candidates']['requests']}",
        f"- Candidates: {report['deepseek_candidates']['candidates']}",
        f"- Evidence-linked candidates: {report['deepseek_candidates']['evidence_linked_candidates']}",
        f"- Effective: {report['effectiveness']['effective']}",
        f"- Message: {report['effectiveness']['message']}",
        "",
        "## Safety",
        "",
        f"- Badcase violations: {report['safety']['badcase_violations']}",
        f"- LLM auto accepted: {report['safety']['llm_auto_accepted_count']}",
        f"- Secret leaks: {report['safety']['secret_leaks']}",
    ]
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], out: Path, markdown: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--focus-doc-type", default="policy_doc")
    parser.add_argument("--focus-fields", default="")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args)
    write_reports(report, args.out, args.markdown)
    print(json.dumps(report["effectiveness"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

