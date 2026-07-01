import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_summary_faithfulness.py"
GOLD_PATH = ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
UIR_DIR = ROOT / "examples" / "real_world" / "uir"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_summary_faithfulness", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_evaluate_summary_sample_detects_unfaithful_facts() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["b1"],
        "summary_must_include": ["适用对象", "申报条件"],
        "summary_must_not_include": ["不存在的补贴金额"],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": (
            "适用对象为企业，申报条件见正文。"
            "2026年出现不存在的补贴金额100万元，由不存在机构办理。"
        ),
        "source_block_ids": ["b1"],
    }
    source_text = "适用对象为企业，申报条件见正文。"

    result = module.evaluate_summary_sample(sample, [chunk], source_text)

    assert result["passed"] is False
    assert result["new_date_violations"] == ["2026年"]
    assert result["new_amount_violations"] == ["100万元"]
    assert result["must_not_include_violations"] == ["不存在的补贴金额"]


def test_table_number_check_detects_values_swapped_between_rows() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "甲项目金额200万元，乙项目金额100万元。",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "甲项目金额100万元，乙项目金额200万元。",
        table_rows=[["项目", "金额"], ["甲项目", "100万元"], ["乙项目", "200万元"]],
    )

    assert result["table_number_violations"]
    assert result["passed"] is False


def test_table_number_check_detects_values_swapped_between_columns() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "甲项目一季度200万元，二季度100万元。",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "甲项目一季度100万元，二季度200万元。",
        table_rows=[
            ["项目", "一季度", "二季度"],
            ["甲项目", "100万元", "200万元"],
        ],
    )

    assert result["table_number_violations"]
    assert result["passed"] is False


def test_table_number_check_falls_back_for_field_value_rows() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "Firstquarter 200; Secondquarter 100.",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "Firstquarter 100; Secondquarter 200.",
        table_rows=[
            ["Info", "Policy"],
            ["Firstquarter", "100"],
            ["Secondquarter", "200"],
        ],
    )

    assert result["table_number_violations"]
    assert result["passed"] is False


def test_table_number_check_accepts_numeric_column_headers() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "AlphaItem 2024 100; 2025 200.",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "AlphaItem 2024 100; 2025 200.",
        table_rows=[["Item", "2024", "2025"], ["AlphaItem", "100", "200"]],
    )

    assert result["table_number_violations"] == []


def test_table_number_check_detects_swaps_under_numeric_column_headers() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "AlphaItem 2024 200; 2025 100.",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "AlphaItem 2024 100; 2025 200.",
        table_rows=[["Item", "2024", "2025"], ["AlphaItem", "100", "200"]],
    )

    assert result["table_number_violations"] == [
        "AlphaItem/2024:200",
        "AlphaItem/2025:100",
    ]
    assert result["passed"] is False


def test_numeric_column_header_value_is_still_checked_as_a_cell() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "AlphaItem 2024 2024; 2025 200.",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "AlphaItem 2024 100; 2025 200.",
        table_rows=[["Item", "2024", "2025"], ["AlphaItem", "100", "200"]],
    )

    assert result["table_number_violations"] == ["AlphaItem/2024:2024"]
    assert result["passed"] is False


def test_table_number_check_normalizes_equivalent_numeric_formats() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["table-1"],
        "table_block_ids": ["table-1"],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "甲项目金额100万元。",
        "source_block_ids": ["table-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "甲项目金额100.00万元。",
        table_rows=[["项目", "金额"], ["甲项目", "100.00万元"]],
    )

    assert result["table_number_violations"] == []


def test_non_table_numbers_are_not_counted_as_changed_table_numbers() -> None:
    module = load_module()
    sample = {
        "doc_id": "d1",
        "source_block_ids": ["paragraph-1"],
        "table_block_ids": [],
        "summary_must_include": [],
        "summary_must_not_include": [],
    }
    chunk = {
        "chunk_id": "c1",
        "summary": "截至2026年完成。",
        "source_block_ids": ["paragraph-1"],
    }

    result = module.evaluate_summary_sample(
        sample,
        [chunk],
        "截至2025年完成。",
        table_rows=[],
    )

    assert result["table_number_violations"] == []


def test_content_organization_gold_has_summary_labels() -> None:
    rows = load_jsonl(GOLD_PATH)
    assert len(rows) >= 20
    for row in rows:
        assert row["source_block_ids"]
        assert row["expected_content_tags"]
        assert row["expected_management_tags"]
        assert row["expected_quality_tags"]
        assert row["summary_must_include"]
        assert isinstance(row["summary_must_not_include"], list)
        assert "???" not in json.dumps(row, ensure_ascii=False)


def test_run_summary_faithfulness_eval_writes_deterministic_reports(tmp_path: Path) -> None:
    module = load_module()
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    report = module.run_evaluation(
        gold_path=GOLD_PATH,
        uir_dir=UIR_DIR,
        output_json=out_json,
        output_md=out_md,
    )
    first_json = out_json.read_bytes()
    first_md = out_md.read_bytes()
    repeated = module.run_evaluation(
        gold_path=GOLD_PATH,
        uir_dir=UIR_DIR,
        output_json=out_json,
        output_md=out_md,
    )

    assert report == repeated
    assert out_json.read_bytes() == first_json
    assert out_md.read_bytes() == first_md
    assert report["status"] == "completed"
    assert report["sample_count"] >= 20
    assert report["passed"] == report["metrics"]["passed_count"]
    assert report["failed"] == report["metrics"]["failed_count"]
    assert report["pass_rate"] == report["metrics"]["faithfulness_pass_rate"]
    assert {
        "passed",
        "failed",
        "pass_rate",
        "passed_count",
        "failed_count",
        "faithfulness_pass_rate",
        "new_date_violation",
        "new_amount_violation",
        "new_org_violation",
        "new_date_violation_count",
        "new_amount_violation_count",
        "new_org_violation_count",
        "must_include_hit_rate",
        "must_not_include_violation_count",
    } <= report["metrics"].keys()
    assert "Summary Faithfulness" in out_md.read_text(encoding="utf-8")


def test_summary_cli_returns_nonzero_for_invalid_gold(tmp_path: Path) -> None:
    invalid_gold = tmp_path / "invalid.jsonl"
    invalid_gold.write_text(
        json.dumps(
            {
                "doc_id": "real_policy_001_training_platform_rules",
                "source_block_ids": ["not_a_real_block"],
                "summary_must_include": ["x"],
                "summary_must_not_include": [],
                "expected_content_tags": ["policy"],
                "expected_management_tags": ["schema:policy_doc"],
                "expected_quality_tags": ["source_linked"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--gold-path",
            str(invalid_gold),
            "--uir-dir",
            str(UIR_DIR),
            "--output-json",
            str(tmp_path / "summary.json"),
            "--output-md",
            str(tmp_path / "summary.md"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "not_a_real_block" in completed.stderr
