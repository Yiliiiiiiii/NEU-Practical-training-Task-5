import json
from pathlib import Path

from scripts import eval_deepseek_candidate_ablation


def test_deepseek_ablation_reports_no_contribution_without_key(tmp_path: Path) -> None:
    out = tmp_path / "ablation.json"
    markdown = tmp_path / "ablation.md"

    exit_code = eval_deepseek_candidate_ablation.main(
        [
            "--base-url",
            "http://127.0.0.1:9",
            "--dataset",
            "examples\\real_world",
            "--focus-doc-type",
            "policy_doc",
            "--focus-fields",
            "issuer,publish_date",
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["deepseek_candidates"]["configured"] is False
    assert report["deepseek_candidates"]["requests"] == 0
    assert report["safety"]["llm_auto_accepted_count"] == 0
    assert report["safety"]["secret_leaks"] == 0
    assert report["effectiveness"]["effective"] is False
    assert "no measurable contribution" in report["effectiveness"]["message"]
    assert "DeepSeek Candidate Ablation" in markdown.read_text(encoding="utf-8")

