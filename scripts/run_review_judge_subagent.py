"""Run scoped AI review-judge triage for the current evaluation run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codex_review_assistant import (  # noqa: E402
    ReviewApiClient as _BaseReviewApiClient,
)
from scripts.codex_review_assistant import decide_review  # noqa: E402

ReviewApiClient = _BaseReviewApiClient


def _bool_arg(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def _load_doc_ids(path: Path | None) -> list[str]:
    if path is None:
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class ScopedReviewApiClient(ReviewApiClient):
    def list_pending(
        self,
        *,
        run_id: str | None = None,
        dataset_id: str | None = None,
        dataset_split: str | None = None,
        task_batch_id: str | None = None,
        doc_ids: list[str] | None = None,
        doc_type: str | None = None,
        schema_id: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        include_historical: bool = False,
    ) -> list[dict[str, Any]]:
        params: list[tuple[str, str]] = [
            ("status", "pending"),
            ("include_historical", str(include_historical).lower()),
        ]
        for key, value in (
            ("run_id", run_id),
            ("dataset_id", dataset_id),
            ("dataset_split", dataset_split),
            ("task_batch_id", task_batch_id),
            ("doc_type", doc_type),
            ("schema_id", schema_id),
            ("created_after", created_after),
            ("created_before", created_before),
        ):
            if value:
                params.append((key, value))
        for doc_id in doc_ids or []:
            params.append(("doc_ids", doc_id))
        query = "&".join(f"{key}={value}" for key, value in params)
        payload = self._request(f"/api/v1/reviews?{query}")
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]


def _has_scope(args: argparse.Namespace, doc_ids: list[str]) -> bool:
    return any(
        [
            args.run_id,
            args.dataset_id,
            args.dataset_split,
            args.task_batch_id,
            doc_ids,
            args.doc_type,
            args.schema_id,
            args.created_after,
            args.created_before,
        ]
    )


def _doc_type(review: dict[str, Any]) -> str:
    value = review.get("doc_type") or review.get("schema_id") or ""
    return str(value)


def build_scope(
    args: argparse.Namespace,
    reviews: list[dict[str, Any]],
    doc_ids: list[str],
) -> dict[str, Any]:
    scope: dict[str, Any] = {
        "dataset_id": args.dataset_id,
        "include_historical": bool(args.include_historical),
        "doc_count": len({str(review.get("doc_id")) for review in reviews if review.get("doc_id")}),
        "doc_types": sorted({_doc_type(review) for review in reviews if _doc_type(review)}),
    }
    for key in (
        "run_id",
        "dataset_split",
        "task_batch_id",
        "doc_type",
        "schema_id",
        "created_after",
        "created_before",
    ):
        value = getattr(args, key)
        if value:
            scope[key] = value
    if doc_ids:
        scope["doc_ids"] = doc_ids
    return scope


def process_scoped_reviews(
    reviews: list[dict[str, Any]],
    *,
    mode: str,
    apply_decision,
    max_approve: int,
    max_reject: int,
) -> dict[str, Any]:
    if mode not in {"dry-run", "apply-guarded"}:
        raise ValueError(f"unsupported mode: {mode}")
    items: list[dict[str, Any]] = []
    applied_items: list[dict[str, Any]] = []
    kept_pending_items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    applied_approve = 0
    applied_reject = 0

    for review in reviews:
        decision = decide_review(review)
        items.append(decision)
        suggestion = str(decision["decision_suggestion"])
        can_apply = (
            mode == "apply-guarded"
            and bool(decision["safe_to_apply"])
            and (
                (suggestion == "approve" and applied_approve < max_approve)
                or (suggestion == "reject" and applied_reject < max_reject)
            )
        )
        if not can_apply:
            kept_pending_items.append(decision)
            continue
        try:
            apply_decision(str(decision["review_id"]), suggestion)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "review_id": decision["review_id"],
                    "decision": suggestion,
                    "error": str(exc),
                }
            )
            kept_pending_items.append(decision)
            continue
        if suggestion == "approve":
            applied_approve += 1
        elif suggestion == "reject":
            applied_reject += 1
        applied_items.append(decision)

    return {
        "items": items,
        "applied_items": applied_items,
        "kept_pending_items": kept_pending_items,
        "errors": errors,
        "suggest_approve": sum(
            item["decision_suggestion"] == "approve" for item in items
        ),
        "suggest_reject": sum(
            item["decision_suggestion"] == "reject" for item in items
        ),
        "suggest_keep_pending": sum(
            item["decision_suggestion"] == "keep_pending" for item in items
        ),
        "applied_approve": applied_approve,
        "applied_reject": applied_reject,
        "kept_pending": len(kept_pending_items),
        "errors_count": len(errors),
    }


def build_report(
    args: argparse.Namespace,
    reviews: list[dict[str, Any]],
    doc_ids: list[str],
    result: dict[str, Any],
) -> dict[str, Any]:
    mapping_review_required = args.mapping_evaluator_review_required
    review_items_found = len(reviews)
    consistency_note = None
    if (
        mapping_review_required is not None
        and mapping_review_required != review_items_found
    ):
        consistency_note = (
            "Review item count differs from mapping evaluator; possible causes include "
            "field-level vs candidate-level counting, queue persistence, or scope metadata gaps."
        )
    return {
        "scope": build_scope(args, reviews, doc_ids),
        "mode": args.mode,
        "mapping_evaluator_review_required": mapping_review_required,
        "review_items_found": review_items_found,
        "out_of_scope_skipped": None,
        "suggest_approve": result["suggest_approve"],
        "suggest_reject": result["suggest_reject"],
        "suggest_keep_pending": result["suggest_keep_pending"],
        "applied_approve": result["applied_approve"],
        "applied_reject": result["applied_reject"],
        "kept_pending": result["kept_pending"],
        "errors": result["errors_count"],
        "reviewer_type": "ai_review_subagent",
        "reviewer_id": "codex_review_judge_v2",
        "consistency_note": consistency_note,
        "items": result["items"],
        "applied_items": result["applied_items"],
        "kept_pending_items": result["kept_pending_items"],
        "error_items": result["errors"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase G Review Judge Scoped Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "review_items_found",
        "mapping_evaluator_review_required",
        "suggest_approve",
        "suggest_reject",
        "suggest_keep_pending",
        "applied_approve",
        "applied_reject",
        "kept_pending",
        "errors",
    ):
        lines.append(f"| {key} | {report.get(key)} |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "```json",
            json.dumps(report["scope"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Decisions",
            "",
            "| Review | Suggestion | Safe | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["items"]:
        reason = str(item["reason"]).replace("|", "\\|")
        lines.append(
            f"| {item['review_id']} | {item['decision_suggestion']} | "
            f"{str(item['safe_to_apply']).lower()} | {reason} |"
        )
    if report.get("consistency_note"):
        lines.extend(["", "## Consistency Note", "", str(report["consistency_note"])])
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], out_path: Path, markdown_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument("--mode", choices=("dry-run", "apply-guarded"), default="dry-run")
    parser.add_argument("--run-id")
    parser.add_argument("--dataset-id")
    parser.add_argument("--dataset-split")
    parser.add_argument("--task-batch-id")
    parser.add_argument("--doc-ids", nargs="*", default=[])
    parser.add_argument("--doc-ids-file", type=Path)
    parser.add_argument("--doc-type")
    parser.add_argument("--schema-id")
    parser.add_argument("--created-after")
    parser.add_argument("--created-before")
    parser.add_argument("--include-historical", type=_bool_arg, default=False)
    parser.add_argument("--mapping-evaluator-review-required", type=int)
    parser.add_argument("--use-deepseek", action="store_true")
    parser.add_argument("--max-approve", type=int, default=20)
    parser.add_argument("--max-reject", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    doc_ids = [*args.doc_ids, *_load_doc_ids(args.doc_ids_file)]
    if not args.include_historical and not _has_scope(args, doc_ids):
        parser.error(
            "--include-historical false requires --run-id, --dataset-id, "
            "--doc-ids/--doc-ids-file, --doc-type, --schema-id, or a time window"
        )

    client_cls = ReviewApiClient
    if client_cls is _BaseReviewApiClient:
        client_cls = ScopedReviewApiClient
    client = client_cls(
        args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
        retries=args.retries,
    )
    raw_reviews = client.list_pending(
        run_id=args.run_id,
        dataset_id=args.dataset_id,
        dataset_split=args.dataset_split,
        task_batch_id=args.task_batch_id,
        doc_ids=doc_ids,
        doc_type=args.doc_type,
        schema_id=args.schema_id,
        created_after=args.created_after,
        created_before=args.created_before,
        include_historical=args.include_historical,
    )
    reviews = [client.enrich_review(item) for item in raw_reviews]
    result = process_scoped_reviews(
        reviews,
        mode=args.mode,
        apply_decision=client.apply_decision,
        max_approve=max(0, args.max_approve),
        max_reject=max(0, args.max_reject),
    )
    report = build_report(args, reviews, doc_ids, result)
    write_reports(report, args.out, args.markdown)
    print(
        json.dumps(
            {
                "review_items_found": report["review_items_found"],
                "suggest_approve": report["suggest_approve"],
                "suggest_reject": report["suggest_reject"],
                "suggest_keep_pending": report["suggest_keep_pending"],
                "applied_approve": report["applied_approve"],
                "applied_reject": report["applied_reject"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
