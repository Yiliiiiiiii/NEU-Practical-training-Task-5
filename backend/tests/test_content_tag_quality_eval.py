import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_content_tag_quality.py"
GOLD_PATH = ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
UIR_DIR = ROOT / "examples" / "real_world" / "uir"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_content_tag_quality", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_precision_recall_f1_counts_expected_and_unknown_tags() -> None:
    module = load_module()

    metrics = module.score_tag_category(
        expected={"policy", "source_linked"},
        actual={"policy", "extra"},
        known={"policy", "source_linked"},
    )

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["unknown_tag_count"] == 1

    prefixed = module.score_tag_category(
        expected={"schema:policy_doc"},
        actual={"schema:policy_doc", "task:retrieval_heading_aware_doc"},
        known={"schema:policy_doc"},
        known_prefixes=("task:",),
    )
    assert prefixed["unknown_tag_count"] == 0


def test_content_organization_gold_has_tag_quality_labels() -> None:
    rows = load_jsonl(GOLD_PATH)
    assert len(rows) >= 20
    for row in rows:
        assert row["source_block_ids"]
        assert row["expected_content_tags"] == row["expected_tags"]["content"]
        assert row["expected_management_tags"]
        assert row["expected_quality_tags"]


def test_run_content_tag_quality_eval_writes_deterministic_reports(tmp_path: Path) -> None:
    module = load_module()
    out_json = tmp_path / "tags.json"
    out_md = tmp_path / "tags.md"

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
    assert {
        "content_tag_precision",
        "content_tag_recall",
        "content_tag_f1",
        "management_tag_precision",
        "management_tag_recall",
        "management_tag_f1",
        "quality_tag_precision",
        "quality_tag_recall",
        "quality_tag_f1",
        "tag_coverage",
        "unknown_tag_count",
    } <= report["metrics"].keys()
    assert "Content Tag Quality" in out_md.read_text(encoding="utf-8")


def test_tag_quality_cli_returns_nonzero_for_invalid_gold(tmp_path: Path) -> None:
    invalid_gold = tmp_path / "invalid.jsonl"
    invalid_gold.write_text(
        json.dumps(
            {
                "doc_id": "real_policy_001_training_platform_rules",
                "source_block_ids": ["not_a_real_block"],
                "expected_content_tags": ["policy"],
                "expected_management_tags": ["schema:policy_doc"],
                "expected_quality_tags": ["source_linked"],
                "summary_must_include": ["x"],
                "summary_must_not_include": [],
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
            str(tmp_path / "tags.json"),
            "--output-md",
            str(tmp_path / "tags.md"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "not_a_real_block" in completed.stderr
