"""Evaluate the human-review knowledge-loop workflow on real execution state."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_support import EvaluationHttpClient, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "knowledge_loop_eval_report.json"
DEFAULT_MD = ROOT / "reports" / "knowledge_loop_eval_report.md"
DEFAULT_UIR = (
    ROOT
    / "examples"
    / "production_like"
    / "uir"
    / "policy"
    / "policy_002_alias_variants.json"
)
APPROVABLE_REVIEW_PAIRS = {
    ("通知名称", "title"),
    ("制定主体", "issuer"),
}


def select_approvable_reviews(
    reviews: list[dict[str, Any]],
    *,
    task_id: str,
    max_reviews: int,
) -> list[dict[str, Any]]:
    return [
        review
        for review in reviews
        if review.get("task_id") == task_id
        and (
            review.get("source_field_name"),
            review.get("target_field_id"),
        )
        in APPROVABLE_REVIEW_PAIRS
    ][:max_reviews]


def _mapping_counts(mapping_report: dict[str, Any]) -> dict[str, int]:
    mappings = mapping_report.get("mappings", [])
    review_items = mapping_report.get("review_required_items", [])
    unmapped = mapping_report.get("unmapped", [])
    return {
        "accepted": len(mappings) if isinstance(mappings, list) else 0,
        "review_required": len(review_items) if isinstance(review_items, list) else 0,
        "unmapped_required": (
            sum(
                1
                for item in unmapped
                if isinstance(item, dict) and item.get("required")
            )
            if isinstance(unmapped, list)
            else 0
        ),
    }


def _mapping_quality(
    mapping_report: dict[str, Any], execution: dict[str, Any]
) -> dict[str, float]:
    mappings = mapping_report.get("mappings", [])
    review_items = mapping_report.get("review_required_items", [])
    unmapped = mapping_report.get("unmapped", [])
    accepted = (
        sum(
            1
            for item in mappings
            if isinstance(item, dict) and item.get("status") == "accepted"
        )
        if isinstance(mappings, list)
        else 0
    )
    review_count = len(review_items) if isinstance(review_items, list) else 0
    unmapped_required = (
        sum(1 for item in unmapped if isinstance(item, dict) and item.get("required"))
        if isinstance(unmapped, list)
        else int(execution.get("unmapped_required_count", 0))
    )
    denominator = accepted + review_count + unmapped_required
    required_total = accepted + review_count + unmapped_required
    return {
        "recall": accepted / denominator if denominator else 0.0,
        "required_coverage": (
            (required_total - unmapped_required) / required_total
            if required_total
            else 1.0
        ),
    }


def run_loop(
    *,
    client: EvaluationHttpClient,
    schema_id: str,
    template_id: str,
    uir_path: Path = DEFAULT_UIR,
    max_reviews: int = 3,
) -> dict[str, Any]:
    uir = json.loads(uir_path.read_text(encoding="utf-8"))
    imported = client.import_document(uir)
    before_task = client.create_task(
        {
            "doc_id": imported["doc_id"],
            "schema_id": schema_id,
            "template_id": template_id,
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False},
        }
    )
    before_task_id = str(before_task["task_id"])
    before_execution = client.execute_task(before_task_id)
    before_mapping = client.report(before_task_id, "mapping")
    before_quality = _mapping_quality(before_mapping, before_execution)

    before = client.effective_template(schema_id, template_id)
    pending_reviews = select_approvable_reviews(
        [
            review
            for review in client.list_reviews("pending")
            if review.get("schema_id") == schema_id
            and review.get("template_id") == template_id
        ],
        task_id=before_task_id,
        max_reviews=max_reviews,
    )
    approved_reviews = [
        client.approve_review(review["review_id"]) for review in pending_reviews
    ]
    approved_review_ids = {str(review["review_id"]) for review in approved_reviews}
    candidates = client.list_candidates()
    accepted_candidates: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        if (
            candidate.get("schema_id") != schema_id
            or candidate.get("template_id") != template_id
            or str(candidate.get("review_id")) not in approved_review_ids
        ):
            continue
        if candidate.get("status") == "blocked":
            blocked_candidates.append(candidate)
            continue
        if candidate.get("status") == "pending":
            accepted_candidates.append(
                client.accept_candidate(candidate["candidate_id"])
            )
    draft_pack = client.create_pack(schema_id, template_id)
    draft_effective = client.effective_template(schema_id, template_id)
    active_pack = client.activate_pack(draft_pack["pack_id"])
    active_effective = client.effective_template(schema_id, template_id)
    after_task = client.create_task(
        {
            "doc_id": imported["doc_id"],
            "schema_id": schema_id,
            "template_id": template_id,
            "schema_version": "1.0.0",
            "template_version": "1.0.0",
            "options": {"enable_llm_fallback": False},
        }
    )
    after_task_id = str(after_task["task_id"])
    after_execution = client.execute_task(after_task_id)
    after_mapping = client.report(after_task_id, "mapping")
    after_quality = _mapping_quality(after_mapping, after_execution)
    old_mapping_after_activation = client.report(before_task_id, "mapping")
    metrics = client.knowledge_metrics()
    return build_report(
        {
            "before": before,
            "draft_effective": draft_effective,
            "active_effective": active_effective,
            "before_mapping": before_mapping,
            "after_mapping": after_mapping,
            "old_mapping_after_activation": old_mapping_after_activation,
            "approved_reviews": approved_reviews,
            "accepted_candidates": accepted_candidates,
            "blocked_candidates": blocked_candidates,
            "draft_pack": draft_pack,
            "active_pack": active_pack,
            "metrics": metrics,
            "before_recall": before_quality["recall"],
            "after_recall": after_quality["recall"],
            "required_coverage_before": before_quality["required_coverage"],
            "required_coverage_after": after_quality["required_coverage"],
        }
    )


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    before = payload.get("before", {})
    draft_effective = payload.get("draft_effective", {})
    active_effective = payload.get("active_effective", {})
    metrics = payload.get("metrics", {})
    old_snapshot_unchanged = draft_effective == before
    old_mapping_unchanged = (
        payload.get("before_mapping") == payload.get("old_mapping_after_activation")
        if "old_mapping_after_activation" in payload
        else old_snapshot_unchanged
    )
    active_changed = active_effective != before
    draft_no_effect = draft_effective == before
    badcase_violation_count = sum(
        1
        for candidate in payload.get("accepted_candidates", [])
        if isinstance(candidate, dict) and candidate.get("badcase_hit")
    )
    old_snapshot_preserved = old_snapshot_unchanged and old_mapping_unchanged
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "old_snapshot_unchanged": old_snapshot_preserved,
            "active_template_changed": active_changed,
            "approved_review_count": len(payload.get("approved_reviews", [])),
            "accepted_candidate_count": len(payload.get("accepted_candidates", [])),
            "active_packs": metrics.get("active_packs", 0),
            "badcase_violation_count": badcase_violation_count,
            "blocked_candidate_count": len(payload.get("blocked_candidates", [])),
            "before_recall": payload.get("before_recall", 0.0),
            "after_recall": payload.get("after_recall", 0.0),
            "required_coverage_before": payload.get("required_coverage_before", 0.0),
            "required_coverage_after": payload.get("required_coverage_after", 0.0),
        },
        "before_mapping_counts": _mapping_counts(payload.get("before_mapping", {})),
        "after_mapping_counts": _mapping_counts(payload.get("after_mapping", {})),
        "review_required_before": _mapping_counts(
            payload.get("before_mapping", {})
        )["review_required"],
        "review_required_after": _mapping_counts(
            payload.get("after_mapping", {})
        )["review_required"],
        "activated_aliases": {
            item["target_field_id"]: sorted(
                {
                    candidate["alias"]
                    for candidate in payload.get("accepted_candidates", [])
                    if isinstance(candidate, dict)
                    and candidate.get("target_field_id") == item["target_field_id"]
                    and isinstance(candidate.get("alias"), str)
                }
            )
            for item in payload.get("accepted_candidates", [])
            if isinstance(item, dict) and item.get("target_field_id")
        },
        "rejected_candidates_count": int(metrics.get("rejected_candidates", 0)),
        "badcase_blocked_count": len(payload.get("blocked_candidates", [])),
        "draft_pack_no_effect": draft_no_effect,
        "active_pack_effect": active_changed,
        "old_snapshot_unchanged": old_snapshot_preserved,
        "badcase_violations": badcase_violation_count,
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
    parser.add_argument("--schema-id", default="policy_doc")
    parser.add_argument("--template-id", default="policy_doc_base_v1")
    parser.add_argument("--uir", type=Path, default=DEFAULT_UIR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "operation",
        nargs="?",
        default="run",
        choices=[
            "run",
            "list-reviews",
            "approve-review",
            "list-candidates",
            "accept-candidate",
            "create-pack",
            "activate-pack",
            "effective-template",
            "metrics",
        ],
    )
    parser.add_argument("--review-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--pack-id")
    args = parser.parse_args()

    client = EvaluationHttpClient(
        args.base_url, api_key=args.api_key, timeout=args.timeout
    )
    if args.operation == "list-reviews":
        write_json(args.out_json, {"items": client.list_reviews("pending")})
        return
    if args.operation == "approve-review":
        if not args.review_id:
            raise SystemExit("--review-id is required")
        write_json(args.out_json, client.approve_review(args.review_id))
        return
    if args.operation == "list-candidates":
        write_json(args.out_json, {"items": client.list_candidates()})
        return
    if args.operation == "accept-candidate":
        if not args.candidate_id:
            raise SystemExit("--candidate-id is required")
        write_json(args.out_json, client.accept_candidate(args.candidate_id))
        return
    if args.operation == "create-pack":
        write_json(args.out_json, client.create_pack(args.schema_id, args.template_id))
        return
    if args.operation == "activate-pack":
        if not args.pack_id:
            raise SystemExit("--pack-id is required")
        write_json(args.out_json, client.activate_pack(args.pack_id))
        return
    if args.operation == "effective-template":
        write_json(
            args.out_json, client.effective_template(args.schema_id, args.template_id)
        )
        return
    if args.operation == "metrics":
        write_json(args.out_json, client.knowledge_metrics())
        return
    report = run_loop(
        client=client,
        schema_id=args.schema_id,
        template_id=args.template_id,
        uir_path=args.uir,
    )
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
