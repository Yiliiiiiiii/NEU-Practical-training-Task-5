"""Evaluate deterministic retrieval quality over real-world organized chunks."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.canonical import CanonicalBlock, CanonicalModel  # noqa: E402
from app.schemas.reports import MappingReport  # noqa: E402
from app.services.chunk_organizer_service import ChunkOrganizerService  # noqa: E402
from app.services.schema_service import SchemaService  # noqa: E402

UIR_DIR = ROOT / "examples" / "real_world" / "uir"
QUERY_PATH = ROOT / "examples" / "real_world" / "retrieval_queries.jsonl"
REPORT_JSON = "chunk_retrieval_eval_report.json"
REPORT_MD = "chunk_retrieval_eval_report.md"

CATALOG = {
    "general_doc": ("general_doc", "general_doc_base_v1"),
    "meeting_doc": ("meeting_doc", "meeting_doc_base_v1"),
    "policy_doc": ("policy_doc", "policy_doc_base_v1"),
    "procurement_doc": ("procurement_doc", "procurement_doc_base_v1"),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    latin = re.findall(r"[a-z0-9]+", lowered)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    chinese = [
        "".join(chinese_chars[index : index + size]).lower()
        for size in (2, 3, 4)
        for index in range(0, max(len(chinese_chars) - size + 1, 0))
    ]
    return [token for token in [*latin, *chinese] if token]


def score_chunk(query: dict[str, Any], chunk: dict[str, Any]) -> float:
    fields = [
        str(chunk.get("text", "")),
        str(chunk.get("summary", "")),
        " ".join(str(item) for item in chunk.get("keywords", [])),
        " ".join(str(item) for item in chunk.get("title_path", [])),
    ]
    searchable = "\n".join(fields).lower()
    terms = tokenize(str(query["query"]))
    score = sum(searchable.count(term) for term in terms)
    score += 25 * sum(
        str(term).lower() in searchable for term in query.get("expected_terms", [])
    )
    return float(score)


def is_relevant(query: dict[str, Any], chunk: dict[str, Any]) -> bool:
    expected = {str(item) for item in query.get("expected_block_ids", [])}
    actual = {str(item) for item in chunk.get("source_block_ids", [])}
    return bool(expected & actual)


def rank_chunks(query: dict[str, Any], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = [
        {
            **chunk,
            "score": score_chunk(query, chunk),
            "relevant": is_relevant(query, chunk),
        }
        for chunk in chunks
    ]
    return sorted(ranked, key=lambda item: (-float(item["score"]), str(item["chunk_id"])))


def recall_at_k(ranked: list[dict[str, Any]], k: int) -> float:
    if not ranked or k <= 0:
        return 0.0
    return 1.0 if any(item.get("relevant") for item in ranked[:k]) else 0.0


def reciprocal_rank(ranked: list[dict[str, Any]]) -> float:
    for index, item in enumerate(ranked, start=1):
        if item.get("relevant"):
            return 1 / index
    return 0.0


def ndcg_at_k(ranked: list[dict[str, Any]], k: int) -> float:
    if not ranked or k <= 0:
        return 0.0
    dcg = 0.0
    for index, item in enumerate(ranked[:k], start=1):
        if item.get("relevant"):
            dcg += 1 / math.log2(index + 1)
    ideal_relevant = sum(1 for item in ranked if item.get("relevant"))
    if ideal_relevant == 0:
        return 0.0
    ideal_count = min(ideal_relevant, k)
    idcg = sum(1 / math.log2(index + 1) for index in range(1, ideal_count + 1))
    return dcg / idcg if idcg else 0.0


def _block_text(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "")
    if text:
        return text
    rows = block.get("attributes", {}).get("rows", [])
    if not isinstance(rows, list):
        return text
    flattened = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        field = str(row.get("field") or "").strip()
        value = str(row.get("value") or "").strip()
        if field or value:
            flattened.append(f"{field}: {value}".strip(": "))
    return "\n".join(flattened)


def canonical_from_uir(uir: dict[str, Any], *, task_id: str, schema_id: str) -> CanonicalModel:
    blocks = [
        CanonicalBlock(
            block_id=str(block["block_id"]),
            type=str(block.get("type", "paragraph")),
            level=block.get("level"),
            text=_block_text(block),
            source_blocks=[str(block["block_id"])],
            source_anchor=block.get("source_anchor"),
        )
        for block in uir.get("blocks", [])
    ]
    return CanonicalModel(
        canonical_version="1.0",
        task_id=task_id,
        doc_id=str(uir["doc_id"]),
        schema_id=schema_id,
        doc_meta={"metadata": uir.get("metadata", {})},
        fields={},
        blocks=blocks,
        assets=[],
    )


def load_uirs(uir_dir: Path = UIR_DIR) -> dict[str, dict[str, Any]]:
    docs = {}
    for path in uir_dir.glob("*/*.json"):
        if path.parent.name == "_rejected":
            continue
        uir = json.loads(path.read_text(encoding="utf-8"))
        docs[str(uir["doc_id"])] = uir
    return docs


def default_options(strategy: str) -> dict[str, Any]:
    return {
        "chunk_strategy": strategy,
        "target_tokens": 160,
        "min_tokens": 32,
        "max_tokens": 260,
        "overlap_tokens": 20,
        "protect_tables": True,
        "protect_lists": True,
        "protect_code_blocks": True,
        "enable_parent_child": strategy == "parent_child",
        "enable_light_semantic_boundary": True,
        "summary_mode": "deterministic",
        "keyword_mode": "deterministic",
    }


def generate_chunks_for_strategy(
    docs: dict[str, dict[str, Any]],
    *,
    strategy: str,
) -> dict[str, list[dict[str, Any]]]:
    schema_service = SchemaService(ROOT / "examples" / "production_like" / "schemas")
    organizer = ChunkOrganizerService()
    chunks_by_doc = {}
    for doc_id, uir in docs.items():
        metadata = uir.get("metadata", {})
        doc_type = str(metadata.get("doc_type", metadata.get("domain")))
        if doc_type not in CATALOG:
            continue
        schema_id, template_id = CATALOG[doc_type]
        schema = schema_service.load_schema(schema_id, "1.0.0")
        task_id = f"retrieval_{strategy}_{doc_id}"
        canonical = canonical_from_uir(uir, task_id=task_id, schema_id=schema_id)
        mapping_report = MappingReport(
            task_id=task_id,
            schema_id=schema_id,
            summary={},
            mappings=[],
            unmapped=[],
            review_required_items=[],
        )
        chunks, _ = organizer.organize_chunks(
            chunks=[],
            canonical_model=canonical,
            schema=schema,
            mapping_report=mapping_report,
            validation_report=None,
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            template_id=template_id,
            template_version="1.0.0",
            options=default_options(strategy),
        )
        chunks_by_doc[doc_id] = chunks
    return chunks_by_doc


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def evaluate(
    queries: list[dict[str, Any]],
    chunks_by_strategy: dict[str, dict[str, list[dict[str, Any]]]],
    *,
    strategies: list[str],
) -> dict[str, Any]:
    if not queries:
        return {
            "status": "no_queries",
            "generated_at": datetime.now(UTC).isoformat(),
            "query_count": 0,
            "strategies": {
                strategy: {
                    "recall@1": 0.0,
                    "recall@3": 0.0,
                    "recall@5": 0.0,
                    "mrr": 0.0,
                    "ndcg@5": 0.0,
                    "source_link_coverage": 0.0,
                    "table_integrity": 0.0,
                    "average_token_estimate": 0.0,
                    "chunk_count": 0,
                }
                for strategy in strategies
            },
            "per_query": [],
            "failure_analysis": [],
        }

    strategy_reports = {}
    per_query = []
    failure_analysis = []
    for strategy in strategies:
        strategy_chunks = chunks_by_strategy.get(strategy, {})
        recalls_1: list[float] = []
        recalls_3: list[float] = []
        recalls_5: list[float] = []
        reciprocal_ranks: list[float] = []
        ndcgs: list[float] = []
        all_chunks = [chunk for chunks in strategy_chunks.values() for chunk in chunks]
        table_queries = 0
        table_hits = 0
        for query in queries:
            chunks = strategy_chunks.get(str(query["doc_id"]), [])
            ranked = rank_chunks(query, chunks)
            top5 = ranked[:5]
            r1 = recall_at_k(ranked, 1)
            r3 = recall_at_k(ranked, 3)
            r5 = recall_at_k(ranked, 5)
            rr = reciprocal_rank(ranked)
            ndcg = ndcg_at_k(ranked, 5)
            recalls_1.append(r1)
            recalls_3.append(r3)
            recalls_5.append(r5)
            reciprocal_ranks.append(rr)
            ndcgs.append(ndcg)
            relevant_rank = next(
                (index for index, item in enumerate(ranked, start=1) if item["relevant"]),
                None,
            )
            if str(query.get("answer_field", "")).endswith("amount") or "table" in str(
                query["query"]
            ).lower():
                table_queries += 1
                if any(item["relevant"] for item in top5):
                    table_hits += 1
            per_query.append(
                {
                    "strategy": strategy,
                    "query_id": query["query_id"],
                    "doc_id": query["doc_id"],
                    "relevant_rank": relevant_rank,
                    "top_chunks": [
                        {
                            "chunk_id": item["chunk_id"],
                            "score": item["score"],
                            "relevant": item["relevant"],
                            "source_block_ids": item.get("source_block_ids", []),
                        }
                        for item in top5
                    ],
                }
            )
            if r5 == 0.0:
                failure_analysis.append(
                    {
                        "strategy": strategy,
                        "query_id": query["query_id"],
                        "reason": "no relevant chunk in top 5",
                        "expected_block_ids": query.get("expected_block_ids", []),
                    }
                )
        linked = [
            chunk
            for chunk in all_chunks
            if chunk.get("source_block_ids") and chunk.get("source_links")
        ]
        token_estimates = [
            float(chunk.get("token_estimate", 0))
            for chunk in all_chunks
            if isinstance(chunk.get("token_estimate", 0), int | float)
        ]
        strategy_reports[strategy] = {
            "recall@1": _mean(recalls_1),
            "recall@3": _mean(recalls_3),
            "recall@5": _mean(recalls_5),
            "mrr": _mean(reciprocal_ranks),
            "ndcg@5": _mean(ndcgs),
            "source_link_coverage": _mean([len(linked) / len(all_chunks)]) if all_chunks else 0.0,
            "table_integrity": round(table_hits / table_queries, 4) if table_queries else 1.0,
            "average_token_estimate": _mean(token_estimates),
            "chunk_count": len(all_chunks),
        }
    return {
        "status": "completed",
        "generated_at": datetime.now(UTC).isoformat(),
        "query_count": len(queries),
        "strategies": strategy_reports,
        "per_query": per_query,
        "failure_analysis": failure_analysis,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Chunk Retrieval Evaluation Report",
        "",
        f"- Status: {report['status']}",
        f"- Query count: {report['query_count']}",
        "",
        "## Strategy metrics",
        "",
        "| Strategy | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | "
        "Source links | Table integrity | Avg tokens | Chunks |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy, metrics in report["strategies"].items():
        lines.append(
            "| {strategy} | {recall1:.4f} | {recall3:.4f} | {recall5:.4f} | "
            "{mrr:.4f} | {ndcg:.4f} | {source:.4f} | {table:.4f} | "
            "{tokens:.2f} | {chunks} |".format(
                strategy=strategy,
                recall1=metrics["recall@1"],
                recall3=metrics["recall@3"],
                recall5=metrics["recall@5"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg@5"],
                source=metrics["source_link_coverage"],
                table=metrics["table_integrity"],
                tokens=metrics["average_token_estimate"],
                chunks=metrics["chunk_count"],
            )
        )
    lines.extend(["", "## Failure analysis", ""])
    if report["failure_analysis"]:
        lines.extend(
            "- {strategy}/{query_id}: {reason}".format(**item)
            for item in report["failure_analysis"]
        )
    else:
        lines.append("- No Recall@5 failures.")
    return "\n".join(lines) + "\n"


def write_reports(output_dir: Path, report: dict[str, Any]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REPORT_JSON
    markdown_path = output_dir / REPORT_MD
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def run_evaluation(
    *,
    query_path: Path = QUERY_PATH,
    output_dir: Path = ROOT / "reports",
    strategies: list[str] | None = None,
) -> dict[str, Any]:
    selected_strategies = strategies or [
        "fixed_window",
        "heading_aware",
        "source_block_aware",
        "table_protect",
    ]
    queries = load_jsonl(query_path)
    needed_docs = {str(query["doc_id"]) for query in queries}
    docs = {
        doc_id: uir
        for doc_id, uir in load_uirs().items()
        if doc_id in needed_docs
    }
    missing_docs = sorted(needed_docs - set(docs))
    chunks_by_strategy = {
        strategy: generate_chunks_for_strategy(docs, strategy=strategy)
        for strategy in selected_strategies
    }
    report = evaluate(queries, chunks_by_strategy, strategies=selected_strategies)
    if missing_docs:
        report["status"] = "missing_docs"
        report["missing_docs"] = missing_docs
    write_reports(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-path", type=Path, default=QUERY_PATH)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["fixed_window", "heading_aware", "source_block_aware", "table_protect"],
    )
    args = parser.parse_args()
    report = run_evaluation(
        query_path=args.query_path,
        output_dir=args.output_dir,
        strategies=args.strategies,
    )
    print(
        {
            "status": report["status"],
            "query_count": report["query_count"],
            "strategies": {
                strategy: metrics["recall@5"]
                for strategy, metrics in report["strategies"].items()
            },
        }
    )


if __name__ == "__main__":
    main()
