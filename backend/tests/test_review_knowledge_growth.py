import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_review_knowledge_growth.py"
FIXTURE_PATH = (
    ROOT
    / "examples"
    / "real_world"
    / "review_fixtures"
    / "next_phase_review_decisions.jsonl"
)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("eval_review_knowledge_growth", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_decisions_reference_fixed_real_uir_values() -> None:
    module = load_module()

    decisions = module.load_decisions(FIXTURE_PATH)

    assert {item["decision"] for item in decisions} == {"approve", "reject"}
    assert all(
        {
            "doc_id",
            "doc_type",
            "source_label",
            "source_value_sample",
            "target_field",
            "decision",
            "reason",
            "expected_alias_to_activate",
        }
        <= item.keys()
        for item in decisions
    )
    assert all(
        item["expected_alias_to_activate"] is None
        or isinstance(item["expected_alias_to_activate"], str)
        for item in decisions
    )
    assert all(
        item["expected_alias_to_activate"] == item["source_label"]
        for item in decisions
        if item["expected_alias_to_activate"] is not None
    )
    assert module.validate_real_uir_references(decisions) == []


def test_full_growth_loop_is_safe_isolated_deterministic_and_improves_metrics(
    tmp_path: Path,
) -> None:
    module = load_module()
    catalog_paths = sorted(
        [
            *(ROOT / "examples" / "production_like" / "schemas").glob("*.json"),
            *(ROOT / "examples" / "production_like" / "mapping_templates").glob("*.json"),
        ]
    )
    catalog_before = {path: path.read_bytes() for path in catalog_paths}

    first = module.run_evaluation(output_dir=tmp_path / "first")
    second = module.run_evaluation(output_dir=tmp_path / "second")

    assert first == second
    assert {path: path.read_bytes() for path in catalog_paths} == catalog_before
    assert first["summary"]["passed"] is True
    assert first["summary"]["isolated_state"] is True
    assert first["summary"]["old_snapshot_unchanged"] is True
    assert first["summary"]["badcase_violation_count"] == 0
    assert first["summary"]["rejected_candidate_activated_count"] == 0
    assert first["draft_pack_no_effect"] is True
    assert first["active_pack_effect"] is True
    assert first["old_snapshot_unchanged"] is True
    assert first["badcase_violations"] == 0
    assert first["rejected_candidates_count"] == 1
    assert first["badcase_blocked_count"] >= 0
    assert first["before_mapping_counts"] == first["before"]
    assert first["after_mapping_counts"] == first["after"]
    assert first["review_required_before"] == first["before"]["review_required_count"]
    assert first["review_required_after"] == first["after"]["review_required_count"]
    assert first["before"]["review_required_count"] > first["after"]["review_required_count"]
    assert first["after"]["auto_mapped_fields"] > first["before"]["auto_mapped_fields"]
    assert first["after"]["mapping_recall"] > first["before"]["mapping_recall"]
    assert first["after"]["required_coverage"] >= first["before"]["required_coverage"]
    assert "strict_pass_count" in first["before"]
    assert "strict_pass_count" in first["after"]
    assert first["activated_aliases"]
    assert first["rejected_controls"]
    assert all(not item["activated"] for item in first["rejected_controls"])
    assert first["draft_pack_evidence"]["affected_future_task"] is False
    assert first["old_task_invariant"]["metadata_unchanged"] is True
    assert first["old_task_invariant"]["canonical_unchanged"] is True
    assert first["old_task_invariant"]["mapping_report_unchanged"] is True
    assert first["old_task_invariant"]["execution_snapshot_unchanged"] is True
    assert first["old_task_invariant"]["task_record_unchanged"] is True
    assert all(
        alias not in aliases
        for alias in first["badcase_controls"]["blocked_aliases"]
        for aliases in first["activated_aliases"].values()
    )
    assert json.loads(
        (tmp_path / "first" / "review_knowledge_growth_report.json").read_text(
            encoding="utf-8"
        )
    ) == first
    assert "# Review Knowledge Growth Report" in (
        tmp_path / "first" / "review_knowledge_growth_report.md"
    ).read_text(encoding="utf-8")


def test_cli_succeeds_without_arguments_and_rejects_invalid_input(tmp_path: Path) -> None:
    success = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert success.returncode == 0, success.stderr

    invalid_fixture = tmp_path / "invalid.jsonl"
    invalid_fixture.write_text('{"decision": "maybe"}\n', encoding="utf-8")
    failure = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--decisions",
            str(invalid_fixture),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode != 0
    assert "error" in failure.stderr.lower()
