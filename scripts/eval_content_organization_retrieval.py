"""Evaluate content-organization retrieval quality over real-world UIR chunks."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval_support import load_jsonl, safe_ratio, write_json, write_markdown

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES = ROOT / "examples" / "real_world" / "gold" / "retrieval_queries.jsonl"
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_JSON = ROOT / "reports" / "content_organization_retrieval_eval.json"
DEFAULT_MD = ROOT / "reports" / "content_organization_retrieval_eval.md"
STRATEGIES = {
    "flat_blocks": {"use_title": False, "use_keywords": False},
    "heading_aware": {"use_title": True, "use_keywords": False},
    "keyword_enriched": {"use_title": True, "use_keywords": True},
    "table_protected": {"use_title": True, "use_keywords": False, "boost_tables": True},
    "hybrid": {"use_title": True, "use_keywords": True, "boost_tables": True},
}


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", value)}


def _chunk_text(chunk: dict[str, Any]) -> str:
    parts: list[str] = []
    text = chunk.get("text")
    if isinstance(text, str):
        parts.append(text)
    title_path = chunk.get("title_path")
    if isinstance(title_path, list):
        parts.extend(str(item) for item in title_path)
    keywords = chunk.get("keywords")
    if isinstance(keywords, list):
        parts.extend(str(item) for item in keywords)
    return " ".join(parts)


def score_chunk(query: str, chunk: dict[str, Any]) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    chunk_tokens = _tokens(_chunk_text(chunk))
    overlap = len(query_tokens & chunk_tokens)
    coverage = safe_ratio(overlap, len(query_tokens))
    density = safe_ratio(overlap, max(len(chunk_tokens), 1))
    return coverage + density


def rank_chunks(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        chunks,
        key=lambda chunk: score_chunk(query, chunk),
        reverse=True,
    )


def strategy_chunks(
    chunks: list[dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:
    config = STRATEGIES[strategy]
    prepared: list[dict[str, Any]] = []
    for chunk in chunks:
        copy = dict(chunk)
        if not config.get("use_title"):
            copy["title_path"] = []
        if not config.get("use_keywords"):
            copy["keywords"] = []
        if config.get("boost_tables") and copy.get("block_type") in {"table", "list"}:
            copy["text"] = f"{copy.get('text', '')} table list structured rows"
        prepared.append(copy)
    return prepared


def is_relevant(chunk: dict[str, Any], gold: dict[str, Any]) -> bool:
    source_block_ids = {
        block_id
        for block_id in chunk.get("source_block_ids", [])
        if isinstance(block_id, str)
    }
    if source_block_ids & set(gold.get("relevant_source_block_ids", [])):
        return True
    title_text = " / ".join(str(item) for item in chunk.get("title_path", []))
    if any(
        expected and expected in title_text
        for expected in gold.get("relevant_title_path_contains", [])
    ):
        return True
    chunk_text = _chunk_text(chunk).lower()
    return any(
        isinstance(keyword, str) and keyword.lower() in chunk_text
        for keyword in gold.get("relevant_keywords", [])
    )


def ranking_metrics(relevance: list[bool]) -> dict[str, float]:
    first_hit = next((index + 1 for index, value in enumerate(relevance) if value), None)
    dcg = 0.0
    ideal_hits = sorted(relevance, reverse=True)
    ideal_dcg = 0.0
    for index, value in enumerate(relevance[:5], start=1):
        if value:
            dcg += 1 / math.log2(index + 1)
    for index, value in enumerate(ideal_hits[:5], start=1):
        if value:
            ideal_dcg += 1 / math.log2(index + 1)
    return {
        "Recall@1": 1.0 if any(relevance[:1]) else 0.0,
        "Recall@3": 1.0 if any(relevance[:3]) else 0.0,
        "Recall@5": 1.0 if any(relevance[:5]) else 0.0,
        "MRR": safe_ratio(1, first_hit) if first_hit else 0.0,
        "nDCG@5": safe_ratio(dcg, ideal_dcg),
    }


def chunks_from_uir(uir: dict[str, Any]) -> list[dict[str, Any]]:
    title = str(uir.get("metadata", {}).get("title", ""))
    chunks: list[dict[str, Any]] = []
    for block in uir.get("blocks", []):
        if not isinstance(block, dict):
            continue
        block_id = block.get("block_id")
        if not isinstance(block_id, str):
            continue
        text = block.get("text")
        chunks.append(
            {
                "chunk_id": block_id,
                "source_block_ids": [block_id],
                "text": text if isinstance(text, str) else "",
                "title_path": [title] if title else [],
                "keywords": sorted(_tokens(f"{title} {text if isinstance(text, str) else ''}"))[:8],
                "block_type": block.get("type"),
            }
        )
    return chunks


def evaluate_strategy(
    queries: list[dict[str, Any]],
    chunks_by_doc_id: dict[str, list[dict[str, Any]]],
    *,
    strategy: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for query in queries:
        chunks = chunks_by_doc_id.get(str(query["doc_id"]), [])
        ranked = rank_chunks(str(query["query"]), strategy_chunks(chunks, strategy))
        relevance = [is_relevant(chunk, query) for chunk in ranked]
        results.append(
            {
                "query_id": query["query_id"],
                "doc_id": query["doc_id"],
                "doc_type": query["doc_type"],
                "strategy": strategy,
                "metrics": ranking_metrics(relevance),
                "top_relevant": bool(relevance[:1] and relevance[0]),
                "chunk_count": len(chunks),
            }
        )
    return results


def _average_metrics(items: list[dict[str, Any]]) -> dict[str, float]:
    keys = ("Recall@1", "Recall@3", "Recall@5", "MRR", "nDCG@5")
    return {
        key: safe_ratio(
            sum(float(item.get("metrics", {}).get(key, 0.0)) for item in items),
            len(items),
        )
        for key in keys
    }


def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_doc_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_strategy[str(item["strategy"])].append(item)
        by_doc_type[str(item["doc_type"])].append(item)
    failures = [item for item in items if not item.get("top_relevant")]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "query_count": len({item["query_id"] for item in items}),
            "result_count": len(items),
            **_average_metrics(items),
        },
        "strategy_comparison": {
            strategy: _average_metrics(strategy_items)
            for strategy, strategy_items in sorted(by_strategy.items())
        },
        "per_document_type": {
            doc_type: _average_metrics(type_items)
            for doc_type, type_items in sorted(by_doc_type.items())
        },
        "per_query_failure_cases": failures[:20],
        "chunk_quality_statistics": {
            "avg_chunk_count": safe_ratio(
                sum(int(item.get("chunk_count", 0)) for item in items),
                len(items),
            )
        },
        "recommendation": (
            "Use the highest-recall strategy as the default, then inspect failure cases "
            "for missing title/table context."
        ),
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Content Organization Retrieval Evaluation",
        "",
        "## Summary",
        "",
        f"- Queries: {report['summary']['query_count']}",
        f"- Mean Recall@3: {report['summary']['Recall@3']:.3f}",
        "",
        "## Strategy Comparison",
        "",
        "| Strategy | Recall@1 | Recall@3 | MRR | nDCG@5 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for strategy, metrics in report["strategy_comparison"].items():
        lines.append(
            f"| {strategy} | {metrics['Recall@1']:.3f} | {metrics['Recall@3']:.3f} | "
            f"{metrics['MRR']:.3f} | {metrics['nDCG@5']:.3f} |"
        )
    lines.extend(["", "## Per Document Type", ""])
    for doc_type, metrics in report["per_document_type"].items():
        lines.append(f"- {doc_type}: Recall@3={metrics['Recall@3']:.3f}")
    lines.extend(["", "## Per Query Failure Cases", ""])
    if report["per_query_failure_cases"]:
        for item in report["per_query_failure_cases"]:
            lines.append(f"- {item['query_id']} ({item['strategy']})")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Chunk Quality Statistics",
            "",
            f"- Average chunk count: {report['chunk_quality_statistics']['avg_chunk_count']:.2f}",
            "",
            "## Recommendation",
            "",
            f"- {report['recommendation']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_chunks(uir_dir: Path) -> dict[str, list[dict[str, Any]]]:
    chunks_by_doc_id = {}
    for path in uir_dir.rglob("*.json"):
        uir = json.loads(path.read_text(encoding="utf-8"))
        chunks_by_doc_id[uir["doc_id"]] = chunks_from_uir(uir)
    return chunks_by_doc_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--uir-dir", type=Path, default=DEFAULT_UIR_DIR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    queries = load_jsonl(args.queries)
    chunks_by_doc_id = _load_chunks(args.uir_dir)
    items: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        items.extend(evaluate_strategy(queries, chunks_by_doc_id, strategy=strategy))
    report = build_report(items)
    write_json(args.out_json, report)
    write_markdown(args.out_md, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
