import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_mapping_overfit_risk  # noqa: E402


def test_overfit_scanner_reports_sample_text_and_path_specific_risks(tmp_path) -> None:
    risky = tmp_path / "candidate_rules.py"
    risky.write_text(
        "\n".join(
            [
                "if '汨罗市第13届人民政府第47次会议' in compact_text:",
                "    source_name = 'meeting sentence'",
                "source_path = 'examples/real_world/uir/meeting/real_meeting_001.json'",
                "title_hint = '2025年人工智能产业及赋能新型工业化创新任务'",
            ]
        ),
        encoding="utf-8",
    )

    report = check_mapping_overfit_risk.build_report([tmp_path])

    summary = report["summary"]
    assert summary["sample_text_snippet_findings"] >= 1
    assert summary["source_path_specific_findings"] >= 1
    assert summary["real_title_snippet_findings"] >= 1
    assert summary["risk_level"] == "high"
    assert report["findings"]["sample_text_snippets"]
    assert report["findings"]["source_path_specific"]
    assert report["findings"]["real_title_snippets"]
