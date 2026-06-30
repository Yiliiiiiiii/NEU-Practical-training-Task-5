import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "eval_chunk_retrieval.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_chunk_retrieval", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recall_mrr_and_ndcg() -> None:
    module = load_module()
    ranked = [{"relevant": False}, {"relevant": True}, {"relevant": False}]

    assert module.recall_at_k(ranked, 1) == 0.0
    assert module.recall_at_k(ranked, 3) == 1.0
    assert module.reciprocal_rank(ranked) == 0.5
    assert module.ndcg_at_k(ranked, 5) == pytest.approx(1 / math.log2(3))


def test_empty_queries_and_chunks_write_reports(tmp_path: Path) -> None:
    module = load_module()

    result = module.evaluate([], {}, strategies=["fixed_window"])
    paths = module.write_reports(tmp_path, result)

    assert result["status"] == "no_queries"
    assert paths["json"].is_file()
    assert paths["markdown"].is_file()


def test_tokenization_and_stable_chunk_scoring() -> None:
    module = load_module()
    query = {
        "query": "预算金额 budget",
        "expected_terms": ["预算金额"],
        "expected_block_ids": ["b2"],
    }
    chunks = [
        {"chunk_id": "c2", "text": "预算金额为56万元", "source_block_ids": ["b2"]},
        {"chunk_id": "c1", "text": "预算说明", "source_block_ids": ["b1"]},
    ]

    ranked = module.rank_chunks(query, chunks)

    assert ranked[0]["chunk_id"] == "c2"
    assert ranked[0]["relevant"] is True


def test_real_fixture_evaluation_generates_strategy_metrics(tmp_path: Path) -> None:
    module = load_module()

    result = module.run_evaluation(output_dir=tmp_path, strategies=["source_block_aware"])

    assert result["status"] == "completed"
    assert result["query_count"] >= 4
    assert result["strategies"]["source_block_aware"]["recall@5"] >= 0.75
    assert result["strategies"]["source_block_aware"]["source_link_coverage"] == 1.0
    assert result["per_query"]
