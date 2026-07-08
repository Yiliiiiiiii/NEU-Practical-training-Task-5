import json
from pathlib import Path

from scripts import apply_phase_h_review_approvals_safe, run_phase_h_review_subagents


def test_phase_h_review_subagents_report_safe_noop(tmp_path: Path) -> None:
    drilldown = tmp_path / "drilldown.json"
    drilldown.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "doc_id": "doc-a",
                        "doc_type": "policy_doc",
                        "target_field": "publish_date",
                        "gap_type": "candidate_not_extracted",
                        "source_anchor_present": False,
                        "risk": "low",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "review.json"
    markdown = tmp_path / "review.md"

    exit_code = run_phase_h_review_subagents.main(
        [
            "--drilldown",
            str(drilldown),
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["subagent_reviewed"] == 1
    assert report["subagent_approved"] == 0
    assert report["needs_human"] == 1
    assert report["llm_auto_accepted_count"] == 0
    assert report["badcase_violations"] == 0
    assert "Phase H Review Subagent Report" in markdown.read_text(encoding="utf-8")


def test_phase_h_safe_apply_does_not_activate_without_approvals(tmp_path: Path) -> None:
    review_report = tmp_path / "review.json"
    review_report.write_text(
        json.dumps({"items": [], "subagent_approved": 0}, ensure_ascii=False),
        encoding="utf-8",
    )
    out = tmp_path / "growth.json"
    markdown = tmp_path / "growth.md"

    exit_code = apply_phase_h_review_approvals_safe.main(
        [
            "--review-report",
            str(review_report),
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["old_snapshot_unchanged"] is True
    assert report["activated_aliases_or_patterns"] == []
    assert report["rejected_candidates_activated"] == 0
    assert report["llm_auto_accepted_count"] == 0
    assert report["badcase_violations"] == 0
    assert "Phase H Review Knowledge Growth" in markdown.read_text(encoding="utf-8")
