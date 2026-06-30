"""Build an inventory report for the real-world UIR evaluation dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from real_world_uir_common import DATASET_DIR, ROOT, dataset_paths, markdown_cell

REPORT_JSON = ROOT / "reports" / "real_world_dataset_inventory.json"
REPORT_MD = ROOT / "reports" / "real_world_dataset_inventory.md"
SOURCE_PATH_SEGMENT = re.compile(r"^(?P<name>[^\[\]]+)(?:\[(?P<index>\*|\d+)\])?$")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(row)
    return rows


def load_uirs(uir_dir: Path) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(uir_dir.glob("*/*.json")):
        if path.parent.name == "_rejected":
            continue
        document = read_json(path)
        doc_id = str(document["doc_id"])
        document["_inventory_path"] = path
        documents[doc_id] = document
    return documents


def source_path_exists(document: dict[str, Any], source_path: str) -> bool:
    nodes: list[Any] = [document]
    for segment in source_path.split("."):
        match = SOURCE_PATH_SEGMENT.fullmatch(segment)
        if match is None:
            return False
        name = match.group("name")
        index = match.group("index")
        next_nodes: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict) or name not in node:
                return False
            value = node[name]
            if index is None:
                next_nodes.append(value)
            elif not isinstance(value, list) or not value:
                return False
            elif index == "*":
                next_nodes.extend(value)
            else:
                position = int(index)
                if position >= len(value):
                    return False
                next_nodes.append(value[position])
        nodes = next_nodes
    return bool(nodes)


def block_ids(document: dict[str, Any]) -> set[str]:
    return {
        str(block.get("block_id"))
        for block in document.get("blocks", [])
        if isinstance(block, dict) and block.get("block_id")
    }


def count_duplicates(values: list[str]) -> int:
    counts = Counter(values)
    return sum(count - 1 for count in counts.values() if count > 1)


def issue(issues: list[dict[str, str]], code: str, message: str) -> None:
    issues.append({"code": code, "message": message})


def dataset_artifact_paths(paths: dict[str, Path]) -> dict[str, Path]:
    root = paths["root"]
    return {
        "manifest": paths["manifest"],
        "uir": paths["uir"],
        "mapping_gold": root / "gold" / "mapping_gold.jsonl",
        "badcases": root / "gold" / "real_world_badcases.jsonl",
        "retrieval_queries": root / "gold" / "retrieval_queries.jsonl",
    }


def validate_block_references(
    *,
    rows: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    row_id_key: str,
    block_key: str,
    issues: list[dict[str, str]],
) -> int:
    invalid = 0
    for row in rows:
        doc_id = str(row.get("doc_id", ""))
        document = uirs.get(doc_id)
        references = row.get(block_key, [])
        if not isinstance(references, list):
            references = []
        actual_block_ids = block_ids(document) if document else set()
        for block_id in references:
            if str(block_id) not in actual_block_ids:
                invalid += 1
                issue(
                    issues,
                    "invalid_block_reference",
                    f"{row_id_key}={row.get(row_id_key)} references missing block "
                    f"{block_id} for {doc_id}",
                )
    return invalid


def validate_query_references(
    *,
    rows: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    issues: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], int, int]:
    valid_rows: list[dict[str, Any]] = []
    invalid_queries = 0
    invalid_blocks = 0
    for row in rows:
        query_id = row.get("query_id")
        doc_id = str(row.get("doc_id", ""))
        references = row.get("relevant_source_block_ids")
        if not isinstance(references, list) or not references:
            invalid_queries += 1
            issue(
                issues,
                "invalid_query_references",
                f"query_id={query_id} must contain a non-empty "
                "relevant_source_block_ids list",
            )
            continue

        actual_block_ids = block_ids(uirs[doc_id]) if doc_id in uirs else set()
        missing_block_ids = [
            str(block_id)
            for block_id in references
            if str(block_id) not in actual_block_ids
        ]
        if missing_block_ids:
            invalid_queries += 1
            invalid_blocks += len(missing_block_ids)
            for block_id in missing_block_ids:
                issue(
                    issues,
                    "invalid_block_reference",
                    f"query_id={query_id} references missing block "
                    f"{block_id} for {doc_id}",
                )
            issue(
                issues,
                "invalid_query_references",
                f"query_id={query_id} has invalid block references for {doc_id}",
            )
            continue
        valid_rows.append(row)
    return valid_rows, invalid_queries, invalid_blocks


def validate_source_paths(
    *,
    rows: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    issues: list[dict[str, str]],
) -> int:
    invalid = 0
    for row in rows:
        doc_id = str(row.get("doc_id", ""))
        document = uirs.get(doc_id)
        checks: list[tuple[str, str]] = []
        for mapping in row.get("expected_mappings", []):
            if isinstance(mapping, dict) and mapping.get("source_path"):
                checks.append(("mapping", str(mapping["source_path"])))
        for review in row.get("expected_review_required", []):
            if isinstance(review, dict) and review.get("source_path"):
                checks.append(("review", str(review["source_path"])))
        for badcase in row.get("known_badcases", []):
            evidence = badcase.get("source_evidence") if isinstance(badcase, dict) else None
            source_paths = evidence.get("source_paths", []) if isinstance(evidence, dict) else []
            for source_path in source_paths:
                checks.append(("embedded_badcase", str(source_path)))
        for kind, source_path in checks:
            if document is None or not source_path_exists(document, source_path):
                invalid += 1
                issue(
                    issues,
                    "invalid_source_path_reference",
                    f"{doc_id} {kind} source_path does not exist: {source_path}",
                )
    return invalid


def validate_badcase_references(
    *,
    badcases: list[dict[str, Any]],
    uirs: dict[str, dict[str, Any]],
    issues: list[dict[str, str]],
) -> int:
    invalid = 0
    for badcase in badcases:
        doc_id = str(badcase.get("doc_id", ""))
        document = uirs.get(doc_id)
        evidence = badcase.get("source_evidence")
        source_paths = evidence.get("source_paths", []) if isinstance(evidence, dict) else []
        for source_path in source_paths:
            if document is None or not source_path_exists(document, str(source_path)):
                invalid += 1
                issue(
                    issues,
                    "invalid_badcase_reference",
                    f"case_id={badcase.get('case_id')} references missing "
                    f"source_path {source_path} for {doc_id}",
                )
    return invalid


def build_inventory(paths: dict[str, Path]) -> dict[str, Any]:
    artifacts = dataset_artifact_paths(paths)
    manifest = read_json(artifacts["manifest"])
    manifest_items = manifest.get("items", [])
    if not isinstance(manifest_items, list):
        raise ValueError("source manifest items must be a list")

    uirs = load_uirs(artifacts["uir"])
    mapping_rows = read_jsonl(artifacts["mapping_gold"])
    badcases = read_jsonl(artifacts["badcases"])
    retrieval_queries = read_jsonl(artifacts["retrieval_queries"])
    issues: list[dict[str, str]] = []
    (
        valid_retrieval_queries,
        invalid_query_references,
        invalid_query_blocks,
    ) = validate_query_references(
        rows=retrieval_queries,
        uirs=uirs,
        issues=issues,
    )

    manifest_ids = {str(item.get("source_id")) for item in manifest_items}
    uir_ids = set(uirs)
    gold_doc_ids = {str(row.get("doc_id")) for row in mapping_rows}
    all_query_doc_ids = {str(row.get("doc_id")) for row in retrieval_queries}
    query_doc_ids = {str(row.get("doc_id")) for row in valid_retrieval_queries}
    query_counts = Counter(str(row.get("doc_id")) for row in valid_retrieval_queries)
    insufficient_retrieval_queries = {
        doc_id: query_counts[doc_id]
        for doc_id in uir_ids
        if query_counts[doc_id] < 2
    }

    for doc_id in sorted(manifest_ids - uir_ids):
        issue(issues, "missing_uir", f"manifest item has no live UIR: {doc_id}")
    for doc_id in sorted(uir_ids - manifest_ids):
        issue(issues, "orphan_uir", f"UIR is not present in manifest: {doc_id}")
    for doc_id in sorted(uir_ids - gold_doc_ids):
        issue(issues, "missing_mapping_gold", f"UIR has no mapping gold: {doc_id}")
    for doc_id in sorted(uir_ids - query_doc_ids):
        issue(issues, "missing_retrieval_query", f"UIR has no retrieval query: {doc_id}")
    for doc_id, query_count in sorted(insufficient_retrieval_queries.items()):
        issue(
            issues,
            "insufficient_retrieval_queries",
            f"{doc_id} has {query_count} retrieval "
            f"{'query' if query_count == 1 else 'queries'}; at least 2 required",
        )
    for doc_id in sorted(gold_doc_ids - uir_ids):
        issue(issues, "orphan_mapping_gold", f"mapping gold references missing UIR: {doc_id}")
    for doc_id in sorted(all_query_doc_ids - uir_ids):
        issue(
            issues,
            "orphan_retrieval_query",
            f"retrieval query references missing UIR: {doc_id}",
        )

    duplicate_ids = (
        count_duplicates([str(item.get("source_id")) for item in manifest_items])
        + count_duplicates([str(row.get("doc_id")) for row in mapping_rows])
        + count_duplicates([str(row.get("query_id")) for row in retrieval_queries])
        + count_duplicates([str(row.get("case_id")) for row in badcases])
    )
    if duplicate_ids:
        issue(issues, "duplicate_ids", f"duplicate ID count: {duplicate_ids}")

    invalid_mapping_blocks = validate_block_references(
        rows=mapping_rows,
        uirs=uirs,
        row_id_key="doc_id",
        block_key="relevant_source_block_ids",
        issues=issues,
    )
    invalid_source_paths = validate_source_paths(
        rows=mapping_rows,
        uirs=uirs,
        issues=issues,
    )
    invalid_badcases = validate_badcase_references(
        badcases=badcases,
        uirs=uirs,
        issues=issues,
    )

    by_doc_type = Counter(
        str(document.get("metadata", {}).get("doc_type"))
        for document in uirs.values()
    )
    mapping_counts_by_type: dict[str, list[int]] = defaultdict(list)
    query_counts_by_type: dict[str, list[int]] = defaultdict(list)
    for doc_id, document in uirs.items():
        doc_type = str(document.get("metadata", {}).get("doc_type"))
        mapping_row = next((row for row in mapping_rows if row.get("doc_id") == doc_id), None)
        mapping_count = (
            len(mapping_row.get("expected_mappings", []))
            if isinstance(mapping_row, dict)
            else 0
        )
        mapping_counts_by_type[doc_type].append(mapping_count)
        query_counts_by_type[doc_type].append(query_counts[doc_id])

    field_density = {}
    for doc_type in sorted(by_doc_type):
        mapping_counts = mapping_counts_by_type[doc_type]
        retrieval_counts = query_counts_by_type[doc_type]
        field_density[doc_type] = {
            "documents": by_doc_type[doc_type],
            "avg_expected_mappings": round(
                sum(mapping_counts) / len(mapping_counts), 2
            )
            if mapping_counts
            else 0,
            "avg_retrieval_queries": round(
                sum(retrieval_counts) / len(retrieval_counts), 2
            )
            if retrieval_counts
            else 0,
        }

    badcases_by_doc_type = Counter()
    for badcase in badcases:
        document = uirs.get(str(badcase.get("doc_id")))
        if document:
            badcases_by_doc_type[str(document.get("metadata", {}).get("doc_type"))] += 1

    summary = {
        "manifest_count": len(manifest_ids),
        "uir_count": len(uirs),
        "mapping_gold_count": len(mapping_rows),
        "retrieval_query_count": len(retrieval_queries),
        "valid_retrieval_query_count": len(valid_retrieval_queries),
        "badcase_count": len(badcases),
        "missing_uirs": len(manifest_ids - uir_ids),
        "orphan_uirs": len(uir_ids - manifest_ids),
        "missing_mapping_gold": len(uir_ids - gold_doc_ids),
        "missing_retrieval_queries": len(uir_ids - query_doc_ids),
        "insufficient_retrieval_queries": len(insufficient_retrieval_queries),
        "invalid_query_references": invalid_query_references,
        "orphan_manifest_items": len(manifest_ids - uir_ids),
        "orphan_mapping_gold": len(gold_doc_ids - uir_ids),
        "orphan_retrieval_queries": len(all_query_doc_ids - uir_ids),
        "invalid_block_references": invalid_mapping_blocks + invalid_query_blocks,
        "invalid_source_path_references": invalid_source_paths,
        "invalid_badcase_references": invalid_badcases,
        "duplicate_ids": duplicate_ids,
    }

    return {
        "summary": summary,
        "by_doc_type": dict(sorted(by_doc_type.items())),
        "badcases_by_doc_type": dict(sorted(badcases_by_doc_type.items())),
        "field_density": field_density,
        "issues": issues,
    }


def render_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# Real-world Dataset Inventory",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in inventory["summary"].items():
        lines.append(f"| {markdown_cell(key)} | {markdown_cell(value)} |")
    lines.extend(["", "## Document Types", "", "| Doc type | Documents | Badcases |"])
    lines.append("| --- | ---: | ---: |")
    for doc_type, count in inventory["by_doc_type"].items():
        badcases = inventory["badcases_by_doc_type"].get(doc_type, 0)
        lines.append(f"| {markdown_cell(doc_type)} | {count} | {badcases} |")
    lines.extend(
        [
            "",
            "## Field Density",
            "",
            "| Doc type | Documents | Avg expected mappings | Avg retrieval queries |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for doc_type, density in inventory["field_density"].items():
        lines.append(
            f"| {markdown_cell(doc_type)} | {density['documents']} | "
            f"{density['avg_expected_mappings']} | "
            f"{density['avg_retrieval_queries']} |"
        )
    lines.extend(["", "## Issues", ""])
    if inventory["issues"]:
        for item in inventory["issues"]:
            lines.append(f"- `{item['code']}`: {item['message']}")
    else:
        lines.append("No inventory issues detected.")
    lines.append("")
    return "\n".join(lines)


def write_reports(
    inventory: dict[str, Any],
    *,
    json_path: Path = REPORT_JSON,
    markdown_path: Path = REPORT_MD,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(inventory), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DATASET_DIR,
        help="Path to examples/real_world dataset directory.",
    )
    parser.add_argument("--json", type=Path, default=REPORT_JSON)
    parser.add_argument("--markdown", type=Path, default=REPORT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(dataset_paths(args.dataset_dir))
    write_reports(inventory, json_path=args.json, markdown_path=args.markdown)
    print(f"wrote {args.json}")
    print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
