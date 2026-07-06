"""Safely triage pending mapping reviews through the SchemaPack API."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FORBIDDEN_PAIRS = {
    ("成文日期", "publish_date"),
    ("发布日期", "effective_date"),
    ("retrieved_at", "effective_date"),
    ("主持人", "attendees"),
    ("联系人", "attendees"),
    ("联系人", "service_object"),
    ("承办单位", "issuer"),
    ("解读机构", "issuer"),
    ("预算金额", "award_amount"),
    ("控制价", "award_amount"),
}
SAFE_PAIRS = {
    ("服务对象", "service_object"),
    ("适用对象", "service_object"),
    ("申请条件", "application_conditions"),
    ("办理条件", "application_conditions"),
    ("会议时间", "meeting_date"),
    ("会议议题", "topics"),
    ("发布日期", "publish_date"),
    ("发文机关", "issuer"),
}
LLM_METHODS = {"llm", "llm_fallback", "llm_suggestion"}
NON_DETERMINISTIC_METHODS = {"fuzzy", *LLM_METHODS}


def _label(value: object) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("：", "")
        .replace(":", "")
        .replace(" ", "")
    )


def _field(review: dict[str, Any], *names: str) -> Any:
    for name in names:
        if review.get(name) is not None:
            return review[name]
    return None


def _badcase_hit(review: dict[str, Any]) -> bool:
    badcase = review.get("badcase_filter")
    return bool(
        isinstance(badcase, dict)
        and (badcase.get("blocked") or badcase.get("hit"))
    )


def _decision(
    review: dict[str, Any],
    suggestion: str,
    reason: str,
    *,
    safe: bool,
) -> dict[str, Any]:
    evidence = review.get("evidence") or []
    evidence_summary = json.dumps(evidence, ensure_ascii=False)
    if len(evidence_summary) > 300:
        evidence_summary = evidence_summary[:297] + "..."
    return {
        "review_id": str(review.get("review_id") or ""),
        "task_id": review.get("task_id"),
        "doc_id": review.get("doc_id"),
        "source_label": _field(review, "source_label", "source_field_name"),
        "target_field": _field(review, "target_field", "target_field_id"),
        "decision_suggestion": suggestion,
        "decision_confidence": "high" if safe else "guarded",
        "reason": reason,
        "evidence_summary": evidence_summary,
        "risk_flags": list(review.get("risk_flags") or []),
        "badcase_hit": _badcase_hit(review),
        "would_generate_knowledge": False,
        "generalization_scope": "same_doc_type" if suggestion == "approve" else "none",
        "safe_to_apply": safe,
    }


def decide_review(review: dict[str, Any]) -> dict[str, Any]:
    """Return approve/reject/keep_pending without mutating external state."""
    source_label = _label(
        _field(review, "source_label", "source_field_name")
    )
    target_field = _label(
        _field(review, "target_field", "target_field_id")
    )
    pair = (source_label, target_field)

    if pair in {(_label(source), _label(target)) for source, target in FORBIDDEN_PAIRS}:
        return _decision(
            review,
            "reject",
            f"forbidden pair: {source_label} -> {target_field}",
            safe=True,
        )
    if _badcase_hit(review):
        return _decision(
            review,
            "keep_pending",
            "Badcase filter matched; automatic approval is prohibited.",
            safe=False,
        )

    confidence = float(review.get("confidence") or 0.0)
    confidence_tier = _label(review.get("confidence_tier"))
    if confidence < 0.82 and confidence_tier != "high":
        return _decision(
            review,
            "keep_pending",
            "Confidence is below the safe automatic threshold.",
            safe=False,
        )

    method = _label(
        _field(review, "suggested_by", "method", "strategy")
    )
    if method in LLM_METHODS:
        return _decision(
            review,
            "keep_pending",
            "LLM-only suggestions require human review.",
            safe=False,
        )
    if method in NON_DETERMINISTIC_METHODS:
        return _decision(
            review,
            "keep_pending",
            "Non-deterministic mapping suggestions require human review.",
            safe=False,
        )

    risk_flags = [str(flag) for flag in review.get("risk_flags") or []]
    if any(not flag.startswith("low_risk") for flag in risk_flags):
        return _decision(
            review,
            "keep_pending",
            "Risk flags exceed the low-risk automatic approval boundary.",
            safe=False,
        )

    source_path = review.get("source_path")
    source_blocks = review.get("source_blocks")
    if not source_path or not isinstance(source_blocks, list) or not source_blocks:
        return _decision(
            review,
            "keep_pending",
            "Source trace is incomplete: source_path and source_blocks are required.",
            safe=False,
        )
    if not review.get("evidence"):
        return _decision(
            review,
            "keep_pending",
            "Explicit source evidence is missing.",
            safe=False,
        )

    if target_field == "issuer":
        source_value = str(review.get("source_value") or "")
        if source_label == _label("发布机构"):
            return _decision(
                review,
                "keep_pending",
                "Page publisher metadata alone is insufficient for issuer approval.",
                safe=False,
            )
        if any(separator in source_value for separator in ("、", "；", ";", "和")):
            return _decision(
                review,
                "keep_pending",
                "Joint issuer evidence requires human confirmation.",
                safe=False,
            )

    normalized_safe_pairs = {
        (_label(source), _label(target)) for source, target in SAFE_PAIRS
    }
    if pair not in normalized_safe_pairs:
        return _decision(
            review,
            "keep_pending",
            "No explicit safe approve rule covers this source-target relation.",
            safe=False,
        )
    return _decision(
        review,
        "approve",
        f"Stable high-confidence relation: {source_label} -> {target_field}.",
        safe=True,
    )


def process_reviews(
    reviews: Iterable[dict[str, Any]],
    *,
    mode: str,
    max_approve: int,
    max_reject: int,
    apply_decision: Callable[[str, str], Any],
) -> dict[str, Any]:
    if mode not in {"dry-run", "apply-safe", "export-only"}:
        raise ValueError(f"unsupported mode: {mode}")
    items: list[dict[str, Any]] = []
    applied_items: list[dict[str, Any]] = []
    kept_pending_items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    applied_approve = 0
    applied_reject = 0

    for review in reviews:
        decision = decide_review(review)
        if mode == "export-only":
            decision.update(
                {
                    "decision_suggestion": "keep_pending",
                    "decision_confidence": "export",
                    "reason": "Export-only mode does not make automated decisions.",
                    "safe_to_apply": False,
                }
            )
        items.append(decision)

        suggestion = str(decision["decision_suggestion"])
        can_apply = (
            mode == "apply-safe"
            and decision["safe_to_apply"]
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
        except Exception as exc:  # one API failure must not abort the batch
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
        else:
            applied_reject += 1
        applied_items.append(decision)

    suggestion_counts = {
        name: sum(
            item["decision_suggestion"] == name for item in items
        )
        for name in ("approve", "reject", "keep_pending")
    }
    return {
        "summary": {
            "mode": mode,
            "pending_total": len(items),
            "suggest_approve": suggestion_counts["approve"],
            "suggest_reject": suggestion_counts["reject"],
            "suggest_keep_pending": suggestion_counts["keep_pending"],
            "unsafe_skipped": suggestion_counts["keep_pending"],
            "applied_approve": applied_approve,
            "applied_reject": applied_reject,
            "kept_pending": len(kept_pending_items),
            "errors": len(errors),
        },
        "items": items,
        "applied_items": applied_items,
        "kept_pending_items": kept_pending_items,
        "errors": errors,
    }


class ReviewApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries
        self._mapping_reports: dict[str, dict[str, Any]] = {}

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(0.25 * (2**attempt), 1.0))
        assert last_error is not None
        raise last_error

    def list_pending(self) -> list[dict[str, Any]]:
        payload = self._request("/api/v1/reviews?status=pending")
        items = payload.get("items", []) if isinstance(payload, dict) else []
        return [item for item in items if isinstance(item, dict)]

    def _mapping_report(self, task_id: str) -> dict[str, Any]:
        if task_id not in self._mapping_reports:
            payload = self._request(f"/api/v1/tasks/{task_id}/reports/mapping")
            self._mapping_reports[task_id] = (
                payload if isinstance(payload, dict) else {}
            )
        return self._mapping_reports[task_id]

    def enrich_review(self, review: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(review)
        enriched.setdefault("doc_type", review.get("schema_id"))
        enriched["source_label"] = _field(
            review, "source_label", "source_field_name"
        )
        enriched["target_field"] = _field(
            review, "target_field", "target_field_id"
        )
        confidence = float(review.get("confidence") or 0.0)
        enriched.setdefault(
            "confidence_tier",
            "high" if confidence >= 0.82 else "medium" if confidence >= 0.65 else "low",
        )
        task_id = str(review.get("task_id") or "")
        if not task_id:
            return enriched
        try:
            report = self._mapping_report(task_id)
        except (HTTPError, URLError, TimeoutError):
            return enriched
        review_id = str(review.get("review_id") or "")
        candidates = [
            item
            for item in report.get("review_required_items", [])
            if isinstance(item, dict)
        ]
        match = next(
            (
                item
                for item in candidates
                if (
                    item.get("mapping_id")
                    and review_id.endswith(str(item["mapping_id"]))
                )
                or (
                    item.get("source_path") == review.get("source_path")
                    and item.get("target_field_id")
                    == review.get("target_field_id")
                )
            ),
            None,
        )
        if match is None:
            return enriched
        for source, target in (
            ("value_sample", "source_value"),
            ("evidence", "evidence"),
            ("source_blocks", "source_blocks"),
            ("risk_flags", "risk_flags"),
            ("badcase_filter", "badcase_filter"),
            ("method", "method"),
            ("review_required_reason", "review_required_reason"),
        ):
            enriched[target] = match.get(source)
        return enriched

    def apply_decision(self, review_id: str, decision: str) -> Any:
        return self._request(
            f"/api/v1/reviews/{review_id}/{decision}",
            method="POST",
            payload={
                "reviewer": "codex_review_assistant",
                "comment": "Applied by Phase B+ safe review policy.",
                "create_knowledge_candidate": False,
            },
        )


def _matches_filters(review: dict[str, Any], args: argparse.Namespace) -> bool:
    filters = (
        ("task_id", args.task_id),
        ("doc_type", args.doc_type),
        ("schema_id", args.schema_id),
        ("template_id", args.template_id),
    )
    return all(expected is None or review.get(name) == expected for name, expected in filters)


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Codex Review Assistant",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in summary.items())
    lines.extend(
        [
            "",
            "## Decisions",
            "",
            "| Review | Suggestion | Safe | Reason |",
            "|---|---|---|---|",
        ]
    )
    for item in report["items"]:
        reason = str(item["reason"]).replace("|", "\\|")
        lines.append(
            f"| {item['review_id']} | {item['decision_suggestion']} | "
            f"{str(item['safe_to_apply']).lower()} | {reason} |"
        )
    lines.extend(
        [
            "",
            "Only deterministic safe-list approvals and explicit forbidden-pair "
            "rejections are eligible for apply-safe.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    report: dict[str, Any],
    out_path: str | Path,
    markdown_path: str | Path,
) -> None:
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "apply-safe", "export-only"),
        default="dry-run",
    )
    parser.add_argument("--max-approve", type=int, default=20)
    parser.add_argument("--max-reject", type=int, default=50)
    parser.add_argument("--task-id")
    parser.add_argument("--doc-type")
    parser.add_argument("--schema-id")
    parser.add_argument("--template-id")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = ReviewApiClient(
        args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
        retries=args.retries,
    )
    reviews = [
        enriched
        for item in client.list_pending()
        if _matches_filters(
            enriched := client.enrich_review(item),
            args,
        )
    ]
    report = process_reviews(
        reviews,
        mode=args.mode,
        max_approve=max(0, args.max_approve),
        max_reject=max(0, args.max_reject),
        apply_decision=client.apply_decision,
    )
    write_reports(report, args.out, args.markdown)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
