import json
from pathlib import Path

import pytest
from scripts import run_review_judge_subagent


class FakeReviewClient:
    def __init__(self, *_args, **_kwargs) -> None:
        self.applied: list[tuple[str, str]] = []

    def list_pending(self, **_scope):
        return [
            {
                "review_id": "review_policy",
                "task_id": "task_policy",
                "doc_id": "real_policy_001",
                "schema_id": "policy_doc",
                "template_id": "policy_doc_base_v1",
                "source_field_name": "发布日期",
                "source_value": "2026-02-06",
                "target_field_id": "publish_date",
                "confidence": 0.9,
                "suggested_by": "exact",
                "source_path": "$.blocks.b1.text",
                "source_blocks": ["b1"],
                "evidence": [{"type": "explicit_label"}],
                "risk_flags": [],
                "badcase_filter": {"blocked": False},
            },
            {
                "review_id": "review_general",
                "task_id": "task_general",
                "doc_id": "real_general_001",
                "schema_id": "general_doc",
                "template_id": "general_doc_base_v1",
                "source_field_name": "服务对象",
                "source_value": "企业法人",
                "target_field_id": "service_object",
                "confidence": 0.7,
                "suggested_by": "fuzzy",
                "source_path": "$.blocks.b2.text",
                "source_blocks": ["b2"],
                "evidence": [{"type": "section"}],
                "risk_flags": [],
                "badcase_filter": {"blocked": False},
            },
        ]

    def enrich_review(self, review):
        enriched = dict(review)
        enriched["doc_type"] = review["schema_id"]
        enriched["source_label"] = review["source_field_name"]
        enriched["target_field"] = review["target_field_id"]
        return enriched

    def apply_decision(self, review_id: str, decision: str):
        self.applied.append((review_id, decision))


def test_judge_requires_explicit_scope_when_history_is_disabled(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run_review_judge_subagent.main(
            [
                "--mode",
                "dry-run",
                "--include-historical",
                "false",
                "--out",
                str(tmp_path / "report.json"),
                "--markdown",
                str(tmp_path / "report.md"),
            ]
        )

    assert exc.value.code == 2


def test_judge_scoped_report_contains_phase_g_counts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(run_review_judge_subagent, "ReviewApiClient", FakeReviewClient)
    out = tmp_path / "report.json"
    markdown = tmp_path / "report.md"

    exit_code = run_review_judge_subagent.main(
        [
            "--mode",
            "dry-run",
            "--dataset-id",
            "real_world_non_procurement_50",
            "--doc-type",
            "non_procurement",
            "--include-historical",
            "false",
            "--mapping-evaluator-review-required",
            "2",
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["scope"]["dataset_id"] == "real_world_non_procurement_50"
    assert report["scope"]["include_historical"] is False
    assert report["scope"]["doc_count"] == 2
    assert report["scope"]["doc_types"] == ["general_doc", "policy_doc"]
    assert report["scope"]["doc_type"] == "non_procurement"
    assert report["mapping_evaluator_review_required"] == 2
    assert report["review_items_found"] == 2
    assert report["suggest_approve"] == 1
    assert report["suggest_keep_pending"] == 1
    assert report["applied_approve"] == 0
    assert "Phase G Review Judge Scoped Report" in markdown.read_text(encoding="utf-8")
