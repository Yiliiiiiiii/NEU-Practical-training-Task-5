import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_content_strategy_comparison.py"
GOLD_PATH = ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
UIR_DIR = ROOT / "examples" / "real_world" / "uir"
QUERY_PATH = ROOT / "examples" / "real_world" / "gold" / "retrieval_queries.jsonl"
EXPECTED_STRATEGIES = {
    "fixed_window",
    "heading_aware",
    "source_block_aware",
    "table_protect",
    "parent_child",
}


def load_module():
    spec = importlib.util.spec_from_file_location("eval_content_strategy_comparison", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_uirs() -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in UIR_DIR.glob("*/*.json"):
        if path.parent.name == "_rejected":
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        documents[str(document["doc_id"])] = document
    return documents


def test_evaluate_chunks_exposes_missing_duplicate_and_table_split_evidence() -> None:
    module = load_module()
    gold = {
        "doc_id": "d1",
        "required_block_groups": [["b1"], ["b2"]],
        "table_block_ids": ["b2"],
        "expected_title_paths": [["标题"]],
        "summary_facts": ["事实"],
        "expected_tags": {
            "content": ["policy"],
            "management": ["official_source"],
            "quality": ["source_linked"],
        },
    }
    duplicate_and_missing = [
        {
            "chunk_id": "c1",
            "source_block_ids": ["b1"],
            "source_links": [{"block_id": "b1"}],
            "token_estimate": 4,
            "text": "事实",
            "summary": "事实",
            "title_path": ["标题"],
            "content_tags": ["policy"],
            "management_tags": ["official_source"],
            "quality_tags": ["source_linked"],
        },
        {
            "chunk_id": "c2",
            "source_block_ids": ["b1"],
            "token_estimate": 6,
        },
    ]

    metrics = module.evaluate_chunks(duplicate_and_missing, gold)

    assert metrics["duplicate_rate"] > 0
    assert metrics["required_group_coverage"] == 0.5
    assert metrics["block_coverage"] == 0.5
    assert metrics["missing_block_ids"] == ["b2"]
    assert metrics["duplicate_block_ids"] == ["b1"]
    assert metrics["title_path_coverage"] == 1.0
    assert metrics["summary_fact_coverage"] == 1.0
    assert metrics["expected_tag_coverage"] == 1.0
    assert metrics["source_link_coverage"] == 0.5
    assert metrics["table_split_violation_count"] == 1
    assert metrics["table_split_block_ids"] == ["b2"]

    wrong_link = [
        {
            "chunk_id": "c1",
            "source_block_ids": ["b1"],
            "source_links": [{"block_id": "not_b1"}],
        }
    ]
    wrong_link_metrics = module.evaluate_chunks(wrong_link, gold)
    assert wrong_link_metrics["source_link_coverage"] == 0.0

    split_table = [
        {"chunk_id": "c1", "source_block_ids": ["b2"], "source_links": []},
        {"chunk_id": "c2", "source_block_ids": ["b2"], "source_links": []},
    ]
    table_metrics = module.evaluate_chunks(split_table, gold)
    assert table_metrics["table_split_violation_count"] == 1
    assert table_metrics["table_split_block_ids"] == ["b2"]


def test_evaluate_chunks_requires_group_blocks_in_same_relevant_chunk() -> None:
    module = load_module()
    gold = {
        "doc_id": "d1",
        "required_block_groups": [["b1", "b2"]],
        "table_block_ids": [],
        "expected_title_paths": [["标题"]],
        "summary_facts": ["事实"],
        "expected_tags": {
            "content": ["policy"],
            "management": ["official_source"],
            "quality": ["source_linked"],
        },
    }
    split_group = [
        {
            "chunk_id": "c1",
            "source_block_ids": ["b1"],
            "source_links": [{"block_id": "b1"}],
            "summary": "事实",
            "title_path": ["标题"],
            "content_tags": ["policy"],
            "management_tags": ["official_source"],
            "quality_tags": ["source_linked"],
        },
        {
            "chunk_id": "c2",
            "source_block_ids": ["b2"],
            "source_links": [{"block_id": "b2"}],
            "summary": "事实",
            "title_path": ["标题"],
            "content_tags": ["policy"],
            "management_tags": ["official_source"],
            "quality_tags": ["source_linked"],
        },
    ]

    metrics = module.evaluate_chunks(split_group, gold)

    assert metrics["block_coverage"] == 1.0
    assert metrics["required_group_coverage"] == 0.0


def test_summary_title_and_tag_coverage_ignore_unrelated_chunks() -> None:
    module = load_module()
    gold = {
        "doc_id": "d1",
        "required_block_groups": [["b1"]],
        "table_block_ids": [],
        "expected_title_paths": [["标题"]],
        "summary_facts": ["事实"],
        "expected_tags": {
            "content": ["policy"],
            "management": ["official_source"],
            "quality": ["source_linked"],
        },
    }
    chunks = [
        {
            "chunk_id": "unrelated",
            "source_block_ids": ["other"],
            "source_links": [{"block_id": "other"}],
            "summary": "事实",
            "title_path": ["标题"],
            "content_tags": ["policy"],
            "management_tags": ["official_source"],
            "quality_tags": ["source_linked"],
        },
        {
            "chunk_id": "required",
            "source_block_ids": ["b1"],
            "source_links": [{"block_id": "b1"}],
            "summary": "",
            "title_path": [],
            "content_tags": [],
            "management_tags": [],
            "quality_tags": [],
        },
    ]

    metrics = module.evaluate_chunks(chunks, gold)

    assert metrics["block_coverage"] == 1.0
    assert metrics["title_path_coverage"] == 0.0
    assert metrics["summary_fact_coverage"] == 0.0
    assert metrics["expected_tag_coverage"] == 0.0


def test_gold_covers_real_uir_content_without_placeholders() -> None:
    module = load_module()
    rows = load_jsonl(GOLD_PATH)
    uirs = load_uirs()

    module.validate_gold(rows, uirs)

    assert len(rows) >= 20
    assert len({row["doc_id"] for row in rows}) == len(rows)
    for row in rows:
        uir = uirs[row["doc_id"]]
        blocks = {block["block_id"]: block for block in uir["blocks"]}
        heading_texts = {
            str(block.get("text", ""))
            for block in blocks.values()
            if block.get("type") == "heading"
        }
        assert row["required_block_groups"]
        assert any(len(group) > 1 for group in row["required_block_groups"])
        assert all(group for group in row["required_block_groups"])
        assert all(
            block_id in blocks for group in row["required_block_groups"] for block_id in group
        )
        assert all(
            blocks[block_id]["type"] in {"table", "list"} for block_id in row["table_block_ids"]
        )
        assert row["expected_title_paths"]
        assert all(
            path and all(segment in heading_texts for segment in path)
            for path in row["expected_title_paths"]
        )
        block_texts = {str(block.get("text", "")) for block in blocks.values()}
        assert row["summary_facts"]
        assert all(fact in block_texts for fact in row["summary_facts"])
        metadata = cast(dict[str, Any], uir["metadata"])
        expected_domain_tag = str(metadata["doc_type"]).removesuffix("_doc")
        assert row["expected_tags"] == {
            "content": [expected_domain_tag],
            "management": ["official_source"],
            "quality": ["source_linked"],
        }
        serialized = json.dumps(row, ensure_ascii=False).lower()
        assert "placeholder" not in serialized
        assert "todo" not in serialized


def test_gold_rejects_valid_but_too_small_sample() -> None:
    module = load_module()
    rows = load_jsonl(GOLD_PATH)
    uirs = load_uirs()

    with pytest.raises(ValueError, match="at least 20"):
        module.validate_gold(rows[:1], uirs)


def test_invalid_gold_reference_is_rejected() -> None:
    module = load_module()
    uirs = load_uirs()
    doc_id = next(iter(uirs))
    invalid = [
        {
            "doc_id": doc_id,
            "required_block_groups": [["missing_block"]],
            "table_block_ids": [],
            "expected_title_paths": [["missing title"]],
            "summary_facts": ["missing fact"],
            "expected_tags": {
                "content": ["general"],
                "management": ["official_source"],
                "quality": ["source_linked"],
            },
        }
    ]

    with pytest.raises(ValueError, match="missing_block"):
        module.validate_gold(invalid, uirs)


def test_validate_queries_rejects_empty_query_and_normalizes_expected_terms() -> None:
    module = load_module()
    rows = load_jsonl(GOLD_PATH)
    uirs = load_uirs()
    doc_id = rows[0]["doc_id"]
    block_id = rows[0]["required_block_groups"][0][0]

    normalized = module.validate_queries(
        [
            {
                "query_id": "q1",
                "doc_id": doc_id,
                "query": "Find policy evidence",
                "relevant_source_block_ids": [block_id],
                "relevant_keywords": [],
            }
        ],
        uirs,
        {doc_id},
    )
    assert normalized[0]["expected_terms"]

    with pytest.raises(ValueError, match="query text"):
        module.validate_queries(
            [
                {
                    "query_id": "q2",
                    "doc_id": doc_id,
                    "query": "   ",
                    "relevant_source_block_ids": [block_id],
                }
            ],
            uirs,
            {doc_id},
        )

    with pytest.raises(ValueError, match="query_id"):
        module.validate_queries(
            [
                {
                    "doc_id": doc_id,
                    "query": "Find policy evidence",
                    "relevant_source_block_ids": [block_id],
                }
            ],
            uirs,
            {doc_id},
        )


def test_run_evaluation_uses_all_production_strategies_and_is_deterministic(
    tmp_path: Path,
) -> None:
    module = load_module()
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"

    report = module.run_evaluation(
        gold_path=GOLD_PATH,
        uir_dir=UIR_DIR,
        query_path=QUERY_PATH,
        output_json=out_json,
        output_md=out_md,
    )
    first_json = out_json.read_bytes()
    first_md = out_md.read_bytes()
    repeated = module.run_evaluation(
        gold_path=GOLD_PATH,
        uir_dir=UIR_DIR,
        query_path=QUERY_PATH,
        output_json=out_json,
        output_md=out_md,
    )

    assert report == repeated
    assert out_json.read_bytes() == first_json
    assert out_md.read_bytes() == first_md
    report_markdown = out_md.read_text(encoding="utf-8")
    assert "Title paths" in report_markdown
    assert "Summary facts" in report_markdown
    assert "Expected tags" in report_markdown
    assert report["status"] == "completed"
    assert report["document_count"] >= 20
    assert report["query_count"] >= 40
    assert set(report["strategies"]) == EXPECTED_STRATEGIES
    assert set(report["recommended_strategy_ranking"]) == EXPECTED_STRATEGIES
    for metrics in report["strategies"].values():
        assert {
            "required_group_coverage",
            "block_coverage",
            "duplicate_rate",
            "table_split_violation_count",
            "source_link_coverage",
            "average_chunk_count",
            "average_token_estimate",
            "recall@1",
            "recall@3",
            "recall@5",
            "mrr",
            "ndcg@5",
        } <= metrics.keys()
    assert all(
        {"doc_id", "strategy", "missing_block_ids", "table_split_block_ids"} <= detail.keys()
        for detail in report["failure_details"]
    )


def test_cli_returns_nonzero_for_invalid_gold(tmp_path: Path) -> None:
    invalid_gold = tmp_path / "invalid.jsonl"
    invalid_gold.write_text(
        json.dumps(
            {
                "doc_id": "real_policy_001_training_platform_rules",
                "required_block_groups": [["not_a_real_block"]],
                "table_block_ids": [],
                "expected_title_paths": [["not a real heading"]],
                "summary_facts": ["not a real fact"],
                "expected_tags": {
                    "content": ["policy"],
                    "management": ["official_source"],
                    "quality": ["source_linked"],
                },
            }
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
            "--query-path",
            str(QUERY_PATH),
            "--output-json",
            str(tmp_path / "report.json"),
            "--output-md",
            str(tmp_path / "report.md"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "not_a_real_block" in completed.stderr
