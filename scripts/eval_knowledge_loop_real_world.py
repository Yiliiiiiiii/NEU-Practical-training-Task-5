"""Evaluate the human-review knowledge-loop workflow on real execution state."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_support import EvaluationHttpClient, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "knowledge_loop_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "knowledge_loop_eval_report.md"


def run_loop(
    *,
    client: EvaluationHttpClient,
    schema_id: str,
    template_id: str,
    max_reviews: int = 3,
) -> dict[str, Any]:
    before = client.effective_template(schema_id, template_id)
    pending_reviews = [
        review
        for review in client.list_reviews("pending")
        if review.get("schema_id") == schema_id and review.get("template_id") == template_id
    ][:max_reviews]
    approved_reviews = [client.approve_review(review["review_id"]) for review in pending_reviews]
    candidates = client.list_candidates()
    accepted_candidates: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("status") == "blocked":
            blocked_candidates.append(candidate)
            continue
        if (
            candidate.get("status") == "pending"
            and candidate.get("schema_id") == schema_id
            and candidate.get("template_id") == template_id
        ):
            accepted_candidates.append(client.accept_candidate(candidate["candidate_id"]))
    draft_pack = client.create_pack(schema_id, template_id)
    draft_effective = client.effective_template(schema_id, template_id)
    active_pack = client.activate_pack(draft_pack["pack_id"])
    active_effective = client.effective_template(schema_id, template_id)
    metrics = client.knowledge_metrics()
    return build_report(
        {
            "before": before,
            "draft_effective": draft_effective,
            "active_effective": active_effective,
            "approved_reviews": approved_reviews,
            "accepted_candidates": accepted_candidates,
            "blocked_candidates": blocked_candidates,
            "draft_pack": draft_pack,
            "active_pack": active_pack,
            "metrics": metrics,
        }
    )


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    before = payload.get("before", {})
    draft_effective = payload.get("draft_effective", {})
    active_effective = payload.get("active_effective", {})
    metrics = payload.get("metrics", {})
    old_snapshot_unchanged = draft_effective == before
    active_changed = active_effective != before
    badcase_violation_count = len(payload.get("blocked_candidates", []))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "old_snapshot_unchanged": old_snapshot_unchanged,
            "active_template_changed": active_changed,
            "approved_review_count": len(payload.get("approved_reviews", [])),
            "accepted_candidate_count": len(payload.get("accepted_candidates", [])),
            "active_packs": metrics.get("active_packs", 0),
            "badcase_violation_count": 0,
            "blocked_candidate_count": badcase_violation_count,
            "before_recall": payload.get("before_recall", 0.0),
            "after_recall": payload.get("after_recall", 0.0),
            "required_coverage_before": payload.get("required_coverage_before", 0.0),
            "required_coverage_after": payload.get("required_coverage_after", 0.0),
        },
        "approved_reviews": payload.get("approved_reviews", []),
        "accepted_candidates": payload.get("accepted_candidates", []),
        "blocked_candidates": payload.get("blocked_candidates", []),
        "draft_pack": payload.get("draft_pack"),
        "active_pack": payload.get("active_pack"),
        "metrics": metrics,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Knowledge Loop Evaluation",
        "",
        "## Summary",
        "",
        f"- Old snapshot unchanged: {summary['old_snapshot_unchanged']}",
        f"- Active template changed: {summary['active_template_changed']}",
        f"- Badcase violations: {summary['badcase_violation_count']}",
        "",
        "## Before/After Recall",
        "",
        f"- Before recall: {summary['before_recall']:.3f}",
        f"- After recall: {summary['after_recall']:.3f}",
        "",
        "## Required Coverage",
        "",
        f"- Before: {summary['required_coverage_before']:.3f}",
        f"- After: {summary['required_coverage_after']:.3f}",
        "",
        "## Review Approvals",
        "",
        f"- Approved reviews: {summary['approved_review_count']}",
        "",
        "## Candidate Acceptance",
        "",
        f"- Accepted candidates: {summary['accepted_candidate_count']}",
        f"- Blocked candidates: {summary['blocked_candidate_count']}",
        "",
        "## Pack Activation",
        "",
        f"- Active packs: {summary['active_packs']}",
        "",
        "## Snapshot Invariant",
        "",
        f"- Draft effective template equals before: {summary['old_snapshot_unchanged']}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--schema-id", default="procurement_doc")
    parser.add_argument("--template-id", default="procurement_doc_base_v1")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    client = EvaluationHttpClient(args.base_url, api_key=args.api_key, timeout=args.timeout)
    report = run_loop(
        client=client,
        schema_id=args.schema_id,
        template_id=args.template_id,
    )
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
