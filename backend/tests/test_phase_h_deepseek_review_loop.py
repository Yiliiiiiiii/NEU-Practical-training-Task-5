import json
from pathlib import Path

from scripts import eval_phase_h_deepseek_review_loop


def test_phase_h_deepseek_review_loop_is_safe_noop_without_key(tmp_path: Path) -> None:
    out = tmp_path / "loop.json"
    markdown = tmp_path / "loop.md"

    exit_code = eval_phase_h_deepseek_review_loop.main(
        [
            "--out",
            str(out),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["deepseek_configured"] is False
    assert report["deepseek_requests"] == 0
    assert report["deepseek_candidates"] == 0
    assert report["llm_auto_accepted_count"] == 0
    assert report["badcase_violations"] == 0
    assert report["secret_leaks"] == 0
    assert report["snapshot_mutations"] == 0
    assert report["status"] == "no_op"
    assert "Phase H DeepSeek Review Loop" in markdown.read_text(encoding="utf-8")
