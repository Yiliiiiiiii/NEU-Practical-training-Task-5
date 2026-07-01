"""Smoke-test that a SchemaPack output package can be consumed downstream."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from package_consumption import (  # noqa: E402
    PackageReadError,
    chunk_source_linked,
    filter_chunks_by_granularity,
    read_validated_package,
    search_chunks,
)


def smoke_rag_ingest(
    package_path: Path,
    query: str = "",
    granularity: str = "all",
) -> dict[str, Any]:
    try:
        manifest, chunks = read_validated_package(package_path)
        chunks = filter_chunks_by_granularity(chunks, granularity)
        top_hit = search_chunks(chunks, query)
        query_requested = bool(query.strip())
        passed = top_hit is not None and (
            not query_requested or top_hit.get("_score", 0) > 0
        )
        return {
            "passed": passed,
            "package": str(package_path),
            "query": query,
            "granularity": granularity,
            "chunk_count": len(chunks),
            "manifest_valid": True,
            "top_hit": format_hit(top_hit) if top_hit is not None else None,
            "errors": [] if passed else ["no chunk matched query"],
            "schema_id": manifest.get("generator", {}).get("schema_id"),
            "template_id": manifest.get("generator", {}).get("template_id"),
        }
    except PackageReadError as exc:
        return {
            "passed": False,
            "package": str(package_path),
            "query": query,
            "granularity": granularity,
            "chunk_count": 0,
            "manifest_valid": False,
            "top_hit": None,
            "errors": [str(exc)],
        }


def format_hit(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "score": chunk.get("_score", 0),
        "source_linked": chunk_source_linked(chunk),
        "summary": chunk.get("summary", ""),
        "keywords": chunk.get("keywords", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package", required=True, type=Path, help="Package zip or directory."
    )
    parser.add_argument(
        "--query", default="", help="Keyword query for simple smoke retrieval."
    )
    parser.add_argument(
        "--granularity",
        choices=["child", "parent", "all"],
        default="all",
        help="Filter chunks by granularity before retrieval.",
    )
    args = parser.parse_args()

    result = smoke_rag_ingest(args.package, args.query, granularity=args.granularity)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
