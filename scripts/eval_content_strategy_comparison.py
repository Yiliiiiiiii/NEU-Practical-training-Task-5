"""Compare production content-organization strategies on real-world UIR documents."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = (
    ROOT / "examples" / "real_world" / "gold" / "content_organization_gold.jsonl"
)
DEFAULT_UIR_DIR = ROOT / "examples" / "real_world" / "uir"
DEFAULT_QUERIES = ROOT / "examples" / "real_world" / "gold" / "retrieval_queries.jsonl"
DEFAULT_JSON = ROOT / "reports" / "content_strategy_comparison_report.json"
DEFAULT_MD = ROOT / "reports" / "content_strategy_comparison_report.md"
STRATEGIES = (
    "fixed_window",
    "heading_aware",
    "source_block_aware",
    "table_protect",
    "parent_child",
)


def _load_retrieval_module():
    path = ROOT / "scripts" / "eval_chunk_retrieval.py"
    spec = importlib.util.spec_from_file_location("_content_strategy_retrieval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load retrieval evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RETRIEVAL = _load_retrieval_module()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(row)
    return rows


def load_uirs(uir_dir: Path) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(uir_dir.glob("*/*.json")):
        if path.parent.name == "_rejected":
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        doc_id = str(document.get("doc_id", ""))
        if not doc_id:
            raise ValueError(f"{path}: missing doc_id")
        if doc_id in documents:
            raise ValueError(f"duplicate UIR doc_id: {doc_id}")
        documents[doc_id] = document
    return documents


def _require_string_list(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    return value


def validate_gold(rows: list[dict[str, Any]], uirs: dict[str, dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("content organization gold is empty")
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        doc_id = str(row.get("doc_id", ""))
        label = f"gold row {index} ({doc_id or 'missing doc_id'})"
        if not doc_id or doc_id not in uirs:
            raise ValueError(f"{label}: unknown UIR document")
        if doc_id in seen:
            raise ValueError(f"{label}: duplicate doc_id")
        seen.add(doc_id)

        document = uirs[doc_id]
        blocks = {
            str(block.get("block_id")): block
            for block in document.get("blocks", [])
            if block.get("block_id")
        }
        groups = row.get("required_block_groups")
        if not isinstance(groups, list) or not groups:
            raise ValueError(f"{label}: required_block_groups must be non-empty")
        for group_index, group in enumerate(groups, start=1):
            block_ids = _require_string_list(
                group, label=f"{label}: required_block_groups[{group_index}]"
            )
            for block_id in block_ids:
                if block_id not in blocks:
                    raise ValueError(f"{label}: unknown block reference {block_id}")

        table_block_ids = row.get("table_block_ids")
        if not isinstance(table_block_ids, list) or not all(
            isinstance(item, str) and item for item in table_block_ids
        ):
            raise ValueError(f"{label}: table_block_ids must be a string list")
        for block_id in table_block_ids:
            if block_id not in blocks:
                raise ValueError(
                    f"{label}: unknown table/list block reference {block_id}"
                )
            if blocks[block_id].get("type") not in {"table", "list"}:
                raise ValueError(f"{label}: {block_id} is not a table/list block")

        heading_texts = {
            str(block.get("text", "")).strip()
            for block in blocks.values()
            if block.get("type") == "heading" and str(block.get("text", "")).strip()
        }
        title_paths = row.get("expected_title_paths")
        if not isinstance(title_paths, list) or not title_paths:
            raise ValueError(f"{label}: expected_title_paths must be non-empty")
        for path_index, title_path in enumerate(title_paths, start=1):
            segments = _require_string_list(
                title_path, label=f"{label}: expected_title_paths[{path_index}]"
            )
            for segment in segments:
                if segment not in heading_texts:
                    raise ValueError(f"{label}: unknown heading text {segment!r}")

        block_texts = {
            str(block.get("text", "")).strip()
            for block in blocks.values()
            if str(block.get("text", "")).strip()
        }
        for fact in _require_string_list(
            row.get("summary_facts"), label=f"{label}: summary_facts"
        ):
            if fact not in block_texts:
                raise ValueError(
                    f"{label}: summary fact is not UIR block text: {fact!r}"
                )

        domain_tag = str(document.get("metadata", {}).get("doc_type", "")).removesuffix(
            "_doc"
        )
        expected_tags = row.get("expected_tags")
        if not isinstance(expected_tags, dict):
            raise ValueError(f"{label}: expected_tags must be a tag-category object")
        if set(expected_tags) != {"content", "management", "quality"}:
            raise ValueError(
                f"{label}: expected_tags must contain content/management/quality"
            )
        content_tags = _require_string_list(
            expected_tags.get("content"), label=f"{label}: expected_tags.content"
        )
        management_tags = _require_string_list(
            expected_tags.get("management"),
            label=f"{label}: expected_tags.management",
        )
        quality_tags = _require_string_list(
            expected_tags.get("quality"), label=f"{label}: expected_tags.quality"
        )
        if content_tags != [domain_tag]:
            raise ValueError(
                f"{label}: expected_tags.content must match UIR domain tag "
                f"{domain_tag!r}"
            )
        if management_tags != ["official_source"]:
            raise ValueError(
                f"{label}: expected_tags.management must mark official_source"
            )
        if quality_tags != ["source_linked"]:
            raise ValueError(f"{label}: expected_tags.quality must mark source_linked")
    if len(rows) < 20:
        raise ValueError("content organization gold must contain at least 20 documents")


def validate_queries(
    queries: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    selected_doc_ids: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    query_counts: Counter[str] = Counter()
    for index, query in enumerate(queries, start=1):
        query_id = str(query.get("query_id", "")).strip()
        if not query_id:
            raise ValueError(f"query row {index}: query_id must be non-empty")
        query_text = str(query.get("query", "")).strip()
        if not query_text:
            raise ValueError(f"query row {index} ({query_id}): query text is empty")
        doc_id = str(query.get("doc_id", ""))
        if doc_id not in uirs:
            raise ValueError(f"query row {index}: unknown doc_id {doc_id!r}")
        expected = query.get("expected_block_ids")
        if expected is None:
            expected = query.get("relevant_source_block_ids")
        expected_ids = _require_string_list(
            expected, label=f"query row {index}: expected block ids"
        )
        actual_ids = {
            str(block.get("block_id"))
            for block in uirs[doc_id].get("blocks", [])
            if block.get("block_id")
        }
        unknown = sorted(set(expected_ids) - actual_ids)
        if unknown:
            raise ValueError(
                f"query row {index} ({doc_id}): unknown block references {unknown}"
            )
        if doc_id not in selected_doc_ids:
            continue
        expected_terms = query.get("expected_terms") or query.get(
            "relevant_keywords", []
        )
        if not expected_terms:
            expected_terms = RETRIEVAL.tokenize(query_text)
        expected_terms = _require_string_list(
            expected_terms, label=f"query row {index}: expected_terms"
        )
        normalized = {
            **query,
            "query_id": query_id,
            "query": query_text,
            "expected_block_ids": expected_ids,
            "expected_terms": expected_terms,
        }
        selected.append(normalized)
        query_counts[doc_id] += 1
    missing = sorted(selected_doc_ids - set(query_counts))
    if missing:
        raise ValueError(f"gold documents without retrieval queries: {missing}")
    return selected


def evaluate_chunks(
    chunks: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    required_groups = [
        [str(block_id) for block_id in group]
        for group in gold.get("required_block_groups", [])
    ]
    grouped_required_ids = {
        block_id for group in required_groups for block_id in group
    }
    table_ids = {str(block_id) for block_id in gold.get("table_block_ids", [])}
    required_ids = sorted(grouped_required_ids | table_ids)
    occurrences: Counter[str] = Counter(
        str(block_id)
        for chunk in chunks
        for block_id in chunk.get("source_block_ids", [])
        if block_id
    )
    chunk_block_sets = [
        {str(block_id) for block_id in chunk.get("source_block_ids", []) if block_id}
        for chunk in chunks
    ]
    covered = {block_id for block_id in required_ids if occurrences[block_id]}
    missing = sorted(set(required_ids) - covered)
    duplicate_ids = sorted(
        block_id for block_id, count in occurrences.items() if count > 1
    )
    duplicate_occurrences = sum(
        count - 1 for count in occurrences.values() if count > 1
    )
    table_split_ids = sorted(
        block_id
        for block_id in table_ids
        if occurrences[str(block_id)] != 1
    )
    linked_required_blocks = _linked_required_blocks(chunks, set(required_ids))
    token_estimates = [
        float(chunk["token_estimate"])
        for chunk in chunks
        if isinstance(chunk.get("token_estimate"), int | float)
    ]
    relevant_chunks = [
        chunk
        for chunk, block_ids in zip(chunks, chunk_block_sets, strict=True)
        if block_ids & set(required_ids)
    ]
    actual_title_paths = [
        [str(segment) for segment in chunk.get("title_path", [])]
        for chunk in relevant_chunks
        if chunk.get("title_path")
    ]
    expected_title_paths = [
        [str(segment) for segment in title_path]
        for title_path in gold.get("expected_title_paths", [])
    ]
    covered_title_paths = sum(
        1
        for expected in expected_title_paths
        if any(actual[: len(expected)] == expected for actual in actual_title_paths)
    )
    searchable_text = "\n".join(
        str(chunk.get("summary", "")) for chunk in relevant_chunks
    )
    summary_facts = [str(fact) for fact in gold.get("summary_facts", [])]
    covered_summary_facts = sum(fact in searchable_text for fact in summary_facts)
    expected_tags = _flatten_expected_tags(gold.get("expected_tags", {}))
    actual_tags = {
        "content": {
            str(tag)
            for chunk in relevant_chunks
            for tag in chunk.get("content_tags", [])
            if tag
        },
        "management": {
            str(tag)
            for chunk in relevant_chunks
            for tag in chunk.get("management_tags", [])
            if tag
        },
        "quality": {
            str(tag)
            for chunk in relevant_chunks
            for tag in chunk.get("quality_tags", [])
            if tag
        },
    }
    covered_groups = sum(
        1
        for group in required_groups
        if any(set(group).issubset(block_ids) for block_ids in chunk_block_sets)
    )
    return {
        "required_group_coverage": _ratio(covered_groups, len(required_groups)),
        "block_coverage": _ratio(len(covered), len(required_ids)),
        "duplicate_rate": _ratio(duplicate_occurrences, sum(occurrences.values())),
        "table_split_violation_count": len(table_split_ids),
        "source_link_coverage": _ratio(len(linked_required_blocks), len(required_ids)),
        "average_chunk_count": float(len(chunks)),
        "average_token_estimate": _mean(token_estimates),
        "title_path_coverage": _ratio(covered_title_paths, len(expected_title_paths)),
        "summary_fact_coverage": _ratio(covered_summary_facts, len(summary_facts)),
        "expected_tag_coverage": _category_tag_coverage(expected_tags, actual_tags),
        "missing_block_ids": missing,
        "duplicate_block_ids": duplicate_ids,
        "table_split_block_ids": table_split_ids,
    }


def _linked_required_blocks(
    chunks: list[dict[str, Any]], required_ids: set[str]
) -> set[str]:
    linked_required: set[str] = set()
    for chunk in chunks:
        source_ids = {
            str(block_id)
            for block_id in chunk.get("source_block_ids", [])
            if str(block_id) in required_ids
        }
        if not source_ids or not isinstance(chunk.get("source_links"), list):
            continue
        linked_ids = {
            str(link.get("block_id"))
            for link in chunk.get("source_links", [])
            if isinstance(link, dict) and link.get("block_id")
        }
        linked_required.update(source_ids & linked_ids)
    return linked_required


def _flatten_expected_tags(value: Any) -> dict[str, set[str]]:
    if not isinstance(value, dict):
        return {"content": set(), "management": set(), "quality": set()}
    return {
        category: {str(tag) for tag in value.get(category, []) if tag}
        for category in ("content", "management", "quality")
    }


def _category_tag_coverage(
    expected: dict[str, set[str]], actual: dict[str, set[str]]
) -> float:
    expected_count = sum(len(tags) for tags in expected.values())
    covered_count = sum(
        len(expected_tags & actual.get(category, set()))
        for category, expected_tags in expected.items()
    )
    return _ratio(covered_count, expected_count)


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _block_evidence(uir: dict[str, Any], block_ids: list[str]) -> list[dict[str, Any]]:
    wanted = set(block_ids)
    return [
        {
            "block_id": str(block["block_id"]),
            "type": block.get("type"),
            "text": str(block.get("text", ""))[:240],
            "source_anchor": block.get("source_anchor"),
        }
        for block in uir.get("blocks", [])
        if str(block.get("block_id")) in wanted
    ]


def _retrieval_metrics(
    queries: list[dict[str, Any]],
    chunks_by_doc: dict[str, list[dict[str, Any]]],
    *,
    strategy: str,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    recalls_1: list[float] = []
    recalls_3: list[float] = []
    recalls_5: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    per_query: list[dict[str, Any]] = []
    for query in queries:
        ranked = RETRIEVAL.rank_chunks(
            query, chunks_by_doc.get(str(query["doc_id"]), [])
        )
        recall_1 = RETRIEVAL.recall_at_k(ranked, 1)
        recall_3 = RETRIEVAL.recall_at_k(ranked, 3)
        recall_5 = RETRIEVAL.recall_at_k(ranked, 5)
        rr = RETRIEVAL.reciprocal_rank(ranked)
        ndcg = RETRIEVAL.ndcg_at_k(ranked, 5)
        recalls_1.append(recall_1)
        recalls_3.append(recall_3)
        recalls_5.append(recall_5)
        reciprocal_ranks.append(rr)
        ndcgs.append(ndcg)
        per_query.append(
            {
                "strategy": strategy,
                "query_id": query["query_id"],
                "doc_id": query["doc_id"],
                "expected_block_ids": query["expected_block_ids"],
                "recall@1": recall_1,
                "recall@3": recall_3,
                "recall@5": recall_5,
                "reciprocal_rank": round(rr, 4),
                "ndcg@5": round(ndcg, 4),
                "top_chunks": [
                    {
                        "chunk_id": item["chunk_id"],
                        "relevant": item["relevant"],
                        "score": item["score"],
                        "source_block_ids": item.get("source_block_ids", []),
                    }
                    for item in ranked[:5]
                ],
            }
        )
    return (
        {
            "recall@1": _mean(recalls_1),
            "recall@3": _mean(recalls_3),
            "recall@5": _mean(recalls_5),
            "mrr": _mean(reciprocal_ranks),
            "ndcg@5": _mean(ndcgs),
        },
        per_query,
    )


def _strategy_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
    strategy, metrics = item
    return (
        -float(metrics["recall@5"]),
        -float(metrics["required_group_coverage"]),
        -float(metrics["block_coverage"]),
        int(metrics["table_split_violation_count"]),
        float(metrics["duplicate_rate"]),
        strategy,
    )


def build_report(
    *,
    gold_rows: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    queries: list[dict[str, Any]],
    chunks_by_strategy: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    strategy_reports: dict[str, dict[str, Any]] = {}
    per_document: list[dict[str, Any]] = []
    per_query: list[dict[str, Any]] = []
    failure_details: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        doc_metrics: list[dict[str, Any]] = []
        chunks_by_doc = chunks_by_strategy[strategy]
        for gold in gold_rows:
            doc_id = str(gold["doc_id"])
            metrics = evaluate_chunks(chunks_by_doc.get(doc_id, []), gold)
            doc_result = {"strategy": strategy, "doc_id": doc_id, **metrics}
            doc_metrics.append(metrics)
            per_document.append(doc_result)
            failure_ids = sorted(
                {
                    *metrics["missing_block_ids"],
                    *metrics["duplicate_block_ids"],
                    *metrics["table_split_block_ids"],
                }
            )
            if failure_ids:
                failure_details.append(
                    {
                        "strategy": strategy,
                        "doc_id": doc_id,
                        "missing_block_ids": metrics["missing_block_ids"],
                        "duplicate_block_ids": metrics["duplicate_block_ids"],
                        "table_split_block_ids": metrics["table_split_block_ids"],
                        "block_evidence": _block_evidence(uirs[doc_id], failure_ids),
                    }
                )

        retrieval_metrics, query_results = _retrieval_metrics(
            queries, chunks_by_doc, strategy=strategy
        )
        per_query.extend(query_results)
        for result in query_results:
            if result["recall@5"] == 0.0:
                doc_id = str(result["doc_id"])
                expected_ids = list(result["expected_block_ids"])
                failure_details.append(
                    {
                        "strategy": strategy,
                        "doc_id": doc_id,
                        "query_id": result["query_id"],
                        "missing_block_ids": expected_ids,
                        "duplicate_block_ids": [],
                        "table_split_block_ids": [],
                        "block_evidence": _block_evidence(uirs[doc_id], expected_ids),
                    }
                )

        strategy_reports[strategy] = {
            "required_group_coverage": _mean(
                [float(item["required_group_coverage"]) for item in doc_metrics]
            ),
            "block_coverage": _mean(
                [float(item["block_coverage"]) for item in doc_metrics]
            ),
            "duplicate_rate": _mean(
                [float(item["duplicate_rate"]) for item in doc_metrics]
            ),
            "table_split_violation_count": sum(
                int(item["table_split_violation_count"]) for item in doc_metrics
            ),
            "source_link_coverage": _mean(
                [float(item["source_link_coverage"]) for item in doc_metrics]
            ),
            "average_chunk_count": _mean(
                [float(item["average_chunk_count"]) for item in doc_metrics]
            ),
            "average_token_estimate": _mean(
                [float(item["average_token_estimate"]) for item in doc_metrics]
            ),
            "title_path_coverage": _mean(
                [float(item["title_path_coverage"]) for item in doc_metrics]
            ),
            "summary_fact_coverage": _mean(
                [float(item["summary_fact_coverage"]) for item in doc_metrics]
            ),
            "expected_tag_coverage": _mean(
                [float(item["expected_tag_coverage"]) for item in doc_metrics]
            ),
            **retrieval_metrics,
        }
    ranking = [
        strategy
        for strategy, _ in sorted(strategy_reports.items(), key=_strategy_sort_key)
    ]
    return {
        "status": "completed",
        "document_count": len(gold_rows),
        "query_count": len(queries),
        "strategy_count": len(STRATEGIES),
        "strategies": strategy_reports,
        "recommended_strategy_ranking": ranking,
        "per_document": per_document,
        "per_query": per_query,
        "failure_details": failure_details,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Content Strategy Comparison Report",
        "",
        f"- Status: {report['status']}",
        f"- Documents: {report['document_count']}",
        f"- Queries: {report['query_count']}",
        f"- Recommended ranking: {' > '.join(report['recommended_strategy_ranking'])}",
        "",
        "## Strategy comparison",
        "",
        "| Strategy | Group coverage | Block coverage | Duplicate rate | "
        "Table splits | Source links | Avg chunks | Avg tokens | "
        "Title paths | Summary facts | Expected tags | "
        "Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy in STRATEGIES:
        metrics = report["strategies"][strategy]
        lines.append(
            "| {strategy} | {group:.4f} | {block:.4f} | {duplicate:.4f} | "
            "{table} | {source:.4f} | {chunks:.2f} | {tokens:.2f} | "
            "{title:.4f} | {summary:.4f} | {tags:.4f} | "
            "{r1:.4f} | {r3:.4f} | {r5:.4f} | {mrr:.4f} | {ndcg:.4f} |".format(
                strategy=strategy,
                group=metrics["required_group_coverage"],
                block=metrics["block_coverage"],
                duplicate=metrics["duplicate_rate"],
                table=metrics["table_split_violation_count"],
                source=metrics["source_link_coverage"],
                chunks=metrics["average_chunk_count"],
                tokens=metrics["average_token_estimate"],
                title=metrics["title_path_coverage"],
                summary=metrics["summary_fact_coverage"],
                tags=metrics["expected_tag_coverage"],
                r1=metrics["recall@1"],
                r3=metrics["recall@3"],
                r5=metrics["recall@5"],
                mrr=metrics["mrr"],
                ndcg=metrics["ndcg@5"],
            )
        )
    lines.extend(["", "## Failure details", ""])
    if report["failure_details"]:
        for item in report["failure_details"]:
            evidence = ", ".join(
                block["block_id"] for block in item.get("block_evidence", [])
            )
            lines.append(
                f"- {item['strategy']}/{item['doc_id']}: "
                f"missing={item['missing_block_ids']}, "
                f"duplicates={item['duplicate_block_ids']}, "
                f"table_splits={item['table_split_block_ids']}; "
                f"evidence={evidence or 'none'}"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def write_reports(
    report: dict[str, Any], *, output_json: Path, output_md: Path
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(render_markdown(report), encoding="utf-8")


def run_evaluation(
    *,
    gold_path: Path = DEFAULT_GOLD,
    uir_dir: Path = DEFAULT_UIR_DIR,
    query_path: Path = DEFAULT_QUERIES,
    output_json: Path = DEFAULT_JSON,
    output_md: Path = DEFAULT_MD,
) -> dict[str, Any]:
    gold_rows = load_jsonl(gold_path)
    uirs = load_uirs(uir_dir)
    validate_gold(gold_rows, uirs)
    selected_doc_ids = {str(row["doc_id"]) for row in gold_rows}
    queries = validate_queries(load_jsonl(query_path), uirs, selected_doc_ids)
    selected_uirs = {doc_id: uirs[doc_id] for doc_id in sorted(selected_doc_ids)}
    chunks_by_strategy = {
        strategy: RETRIEVAL.generate_chunks_for_strategy(
            selected_uirs, strategy=strategy
        )
        for strategy in STRATEGIES
    }
    report = build_report(
        gold_rows=gold_rows,
        uirs=uirs,
        queries=queries,
        chunks_by_strategy=chunks_by_strategy,
    )
    write_reports(report, output_json=output_json, output_md=output_md)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-path", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--uir-dir", type=Path, default=DEFAULT_UIR_DIR)
    parser.add_argument("--query-path", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = run_evaluation(
        gold_path=args.gold_path,
        uir_dir=args.uir_dir,
        query_path=args.query_path,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "document_count": report["document_count"],
                "query_count": report["query_count"],
                "recommended_strategy_ranking": report["recommended_strategy_ranking"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
