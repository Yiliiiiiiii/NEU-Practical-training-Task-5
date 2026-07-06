import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import eval_schema_drafts  # noqa: E402


def test_eval_schema_drafts_reports_phase3_safety_metrics(tmp_path) -> None:
    out = tmp_path / "schema_draft_eval_report.json"
    markdown = tmp_path / "schema_draft_eval_report.md"

    report = eval_schema_drafts.run(
        samples_dir=ROOT / "examples" / "real_world" / "uir" / "general",
        out_path=out,
        markdown_path=markdown,
        limit=5,
    )

    assert report["sample_count"] == 5
    assert report["candidate_count"] > 0
    assert report["source_evidence_coverage"] == 1.0
    assert report["risk_scan_ran"] is True
    assert report["must_not_auto_activate"] is True
    assert report["badcase_violations"] == 0
    assert report["llm_auto_accepted_count"] == 0
    assert report["secret_leak_count"] == 0
    assert out.is_file()
    assert markdown.read_text(encoding="utf-8").startswith(
        "# Schema Draft Generator Evaluation"
    )
