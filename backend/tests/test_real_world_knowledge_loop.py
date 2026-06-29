import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_real_world_knowledge_loop.py"
DECISION_PATH = (
    ROOT
    / "examples"
    / "real_world"
    / "review_fixtures"
    / "procurement_review_decisions.jsonl"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "eval_real_world_knowledge_loop",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_review_decisions_requires_approved_and_rejected_cases() -> None:
    module = load_module()

    decisions = module.load_decisions(DECISION_PATH)

    assert {decision["decision"] for decision in decisions} == {"approve", "reject"}
    assert any(
        decision["source_field"] == "采购方名称"
        and decision["target_field"] == "buyer_name"
        for decision in decisions
    )
    assert any(
        decision["source_field"] == "最高限价"
        and decision["target_field"] == "winning_amount"
        for decision in decisions
    )


def test_only_approved_non_badcase_decisions_activate(tmp_path: Path) -> None:
    module = load_module()

    result = module.run_loop(output_dir=tmp_path)

    assert result["approved_candidates"] == 1
    assert result["rejected_candidates"] == 1
    assert result["badcase_violation_count"] == 0
    assert "采购方名称" in result["activated_aliases"]["buyer_name"]
    assert "最高限价" not in result["activated_aliases"].get("winning_amount", [])
    assert result["after"]["auto_mapped_fields"] >= result["before"]["auto_mapped_fields"]
    assert result["after"]["review_required_count"] <= result["before"]["review_required_count"]
    assert result["metrics"]["approved_candidates"] == 1


def test_activation_does_not_mutate_old_snapshot_and_writes_reports(tmp_path: Path) -> None:
    module = load_module()

    result = module.run_loop(output_dir=tmp_path)

    assert result["old_snapshot_unchanged"] is True
    json_report = tmp_path / "real_world_knowledge_loop_report.json"
    markdown_report = tmp_path / "real_world_knowledge_loop_report.md"
    assert json_report.is_file()
    assert markdown_report.is_file()
    assert json.loads(json_report.read_text(encoding="utf-8"))["old_snapshot_unchanged"] is True
    markdown = markdown_report.read_text(encoding="utf-8")
    assert "| Stage | Auto mapped | Review required | Missing required |" in markdown
    assert "采购方名称" in markdown
