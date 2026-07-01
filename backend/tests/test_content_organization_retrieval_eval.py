import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
QUERIES = ROOT / "examples" / "real_world" / "gold" / "retrieval_queries.jsonl"
UIR_DIR = ROOT / "examples" / "real_world" / "uir"


def load_script(name: str) -> ModuleType:
    path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_real_world_retrieval_queries_are_valid_jsonl() -> None:
    rows = load_jsonl(QUERIES)
    uir_by_doc_id = {}
    block_ids_by_doc_id = {}
    for path in UIR_DIR.rglob("*.json"):
        uir = json.loads(path.read_text(encoding="utf-8"))
        uir_by_doc_id[uir["doc_id"]] = uir
        block_ids_by_doc_id[uir["doc_id"]] = {
            block["block_id"] for block in uir["blocks"]
        }

    assert len(rows) >= 32
    assert len({row["doc_id"] for row in rows}) == 30
    assert all(row["query"].strip() for row in rows)
    assert all(
        row["relevant_source_block_ids"]
        or row["relevant_title_path_contains"]
        or row["relevant_keywords"]
        for row in rows
    )
    by_type = Counter(row["doc_type"] for row in rows)
    assert all(
        by_type[name] >= 6
        for name in ("policy_doc", "procurement_doc", "meeting_doc", "general_doc")
    )
    for row in rows:
        assert row["doc_id"] in uir_by_doc_id
        assert row["doc_type"] == uir_by_doc_id[row["doc_id"]]["metadata"]["doc_type"]
        assert set(row["relevant_source_block_ids"]) <= block_ids_by_doc_id[row["doc_id"]]


def test_retrieval_metrics_compute_known_ranking() -> None:
    evaluator = load_script("eval_content_organization_retrieval")

    relevant = [False, True, False, True, False]
    metrics = evaluator.ranking_metrics(relevant)

    assert metrics["Recall@1"] == 0.0
    assert metrics["Recall@3"] == 1.0
    assert metrics["Recall@5"] == 1.0
    assert metrics["MRR"] == 0.5
    assert metrics["nDCG@5"] > 0


def test_score_chunk_ignores_source_block_id() -> None:
    evaluator = load_script("eval_content_organization_retrieval")
    query = "project budget purchaser"
    chunk_a = {
        "chunk_id": "a",
        "source_block_ids": ["block-a"],
        "text": "project budget purchaser",
        "title_path": ["Procurement"],
        "keywords": ["budget"],
    }
    chunk_b = {**chunk_a, "chunk_id": "b", "source_block_ids": ["block-b"]}

    assert evaluator.score_chunk(query, chunk_a) == evaluator.score_chunk(query, chunk_b)


def test_strategy_chunks_apply_title_and_keyword_options() -> None:
    evaluator = load_script("eval_content_organization_retrieval")
    chunks = [
        {
            "chunk_id": "c1",
            "source_block_ids": ["b1"],
            "text": "body",
            "title_path": ["Useful title"],
            "keywords": ["useful"],
        }
    ]

    flat = evaluator.strategy_chunks(chunks, "flat_blocks")
    enriched = evaluator.strategy_chunks(chunks, "keyword_enriched")

    assert flat[0]["title_path"] == []
    assert flat[0]["keywords"] == []
    assert enriched[0]["title_path"] == ["Useful title"]
    assert enriched[0]["keywords"] == ["useful"]


def test_retrieval_eval_builds_report_sections() -> None:
    evaluator = load_script("eval_content_organization_retrieval")

    report = evaluator.build_report(
        [
            {
                "query_id": "q1",
                "doc_type": "procurement_doc",
                "strategy": "heading_aware",
                "metrics": {"Recall@1": 1.0, "Recall@3": 1.0, "MRR": 1.0, "nDCG@5": 1.0},
                "top_relevant": True,
                "chunk_count": 2,
            }
        ]
    )
    markdown = evaluator.render_markdown(report)

    assert report["summary"]["query_count"] == 1
    assert report["strategy_comparison"]["heading_aware"]["Recall@1"] == 1.0
    assert "## Strategy Comparison" in markdown
    assert "## Per Document Type" in markdown
    assert "## Per Query Failure Cases" in markdown
    assert "## Chunk Quality Statistics" in markdown
