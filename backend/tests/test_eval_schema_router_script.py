import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import eval_schema_router  # noqa: E402


def test_eval_schema_router_reports_v2_quality_metrics(tmp_path) -> None:
    out = tmp_path / "schema_router_eval_report.json"
    markdown = tmp_path / "schema_router_eval_report.md"

    report = eval_schema_router.run(
        fixtures_dir=ROOT / "examples" / "external_uir",
        out_path=out,
        markdown_path=markdown,
    )

    assert report["fixture_count"] >= 4
    assert report["top1_accuracy"] >= 0.85
    assert report["top2_accuracy"] >= 0.95
    assert report["unsafe_auto_route_count"] == 0
    assert report["route_evidence_coverage"] == 1.0
    assert report["route_version"] == "2.0"
    assert out.is_file()
    assert markdown.read_text(encoding="utf-8").startswith("# Schema Router v2 Evaluation")
