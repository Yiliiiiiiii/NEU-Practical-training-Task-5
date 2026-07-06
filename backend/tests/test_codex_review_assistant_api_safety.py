import json
from pathlib import Path

from scripts.codex_review_assistant import process_reviews, write_reports


def safe_review(review_id: str) -> dict[str, object]:
    return {
        "review_id": review_id,
        "task_id": "task_1",
        "doc_type": "general_doc",
        "source_label": "申请条件",
        "target_field": "application_conditions",
        "confidence": 0.9,
        "confidence_tier": "high",
        "evidence": [{"type": "section_heading"}],
        "source_path": "$.blocks.b1.text",
        "source_blocks": ["b1"],
        "risk_flags": [],
        "badcase_filter": {"blocked": False},
        "suggested_by": "exact",
    }


def test_dry_run_never_calls_review_decision_api() -> None:
    calls: list[tuple[str, str]] = []

    report = process_reviews(
        [safe_review("r1")],
        mode="dry-run",
        max_approve=20,
        max_reject=50,
        apply_decision=lambda review_id, decision: calls.append(
            (review_id, decision)
        ),
    )

    assert calls == []
    assert report["summary"]["suggest_approve"] == 1
    assert report["summary"]["applied_approve"] == 0


def test_apply_safe_respects_approve_cap() -> None:
    calls: list[tuple[str, str]] = []

    report = process_reviews(
        [safe_review("r1"), safe_review("r2"), safe_review("r3")],
        mode="apply-safe",
        max_approve=2,
        max_reject=50,
        apply_decision=lambda review_id, decision: calls.append(
            (review_id, decision)
        ),
    )

    assert calls == [("r1", "approve"), ("r2", "approve")]
    assert report["summary"]["applied_approve"] == 2
    assert report["summary"]["kept_pending"] == 1


def test_report_files_are_generated(tmp_path: Path) -> None:
    report = process_reviews(
        [safe_review("r1")],
        mode="export-only",
        max_approve=0,
        max_reject=0,
        apply_decision=lambda _review_id, _decision: None,
    )
    json_path = tmp_path / "suggestions.json"
    markdown_path = tmp_path / "suggestions.md"

    write_reports(report, json_path, markdown_path)

    assert json.loads(json_path.read_text(encoding="utf-8"))["items"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Review Assistant" in markdown
    assert "keep_pending" in markdown
