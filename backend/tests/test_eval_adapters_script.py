import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import eval_adapters  # noqa: E402


def test_eval_adapters_reports_phase1_metrics(tmp_path) -> None:
    out = tmp_path / "adapter_framework_eval_report.json"
    markdown = tmp_path / "adapter_framework_eval_report.md"

    report = eval_adapters.run(
        fixtures_dir=ROOT / "examples" / "external_uir",
        out_path=out,
        markdown_path=markdown,
    )

    assert report["adapter_count"] == 2
    assert report["fixture_count"] >= 4
    assert report["adapter_selection_accuracy"] == 1.0
    assert report["uir_validation_pass_rate"] == 1.0
    assert report["trace_coverage_avg"] >= 0.95
    assert report["llm_auto_accepted_count"] == 0
    assert report["badcase_violations"] == 0
    assert out.is_file()
    assert markdown.read_text(encoding="utf-8").startswith("# Adapter Framework Evaluation")
