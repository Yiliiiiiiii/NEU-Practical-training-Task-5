"""Export package chunks as downstream RAG-corpus JSONL."""

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
    training_metadata,
)


def export_rag_corpus(
    package_path: Path,
    output_path: Path,
    *,
    granularity: str = "all",
    include_summary: bool = True,
    include_keywords: bool = True,
    min_chars: int = 0,
    fail_on_missing_source_links: bool = False,
) -> dict[str, Any]:
    manifest, chunks = read_validated_package(package_path)
    chunks = [
        chunk
        for chunk in filter_chunks_by_granularity(chunks, granularity)
        if len(str(chunk.get("text") or "")) >= min_chars
    ]
    missing = sum(not chunk_source_linked(chunk) for chunk in chunks)
    if missing and fail_on_missing_source_links:
        raise ValueError(f"{missing} chunks are missing source links")
    rows = []
    for index, chunk in enumerate(chunks, 1):
        metadata = training_metadata(manifest, chunk)
        tags = metadata.pop("tags", {})
        metadata["content_tags"] = (
            tags.get("content", []) if isinstance(tags, dict) else []
        )
        metadata["management_tags"] = (
            tags.get("management", []) if isinstance(tags, dict) else []
        )
        metadata["quality_tags"] = (
            tags.get("quality", []) if isinstance(tags, dict) else []
        )
        metadata["token_estimate"] = chunk.get("token_estimate")
        if not include_summary:
            metadata.pop("summary", None)
        if not include_keywords:
            metadata.pop("keywords", None)
        rows.append(
            {
                "id": chunk.get("chunk_id") or f"chunk_{index:04d}",
                "text": str(chunk.get("text") or ""),
                "metadata": metadata,
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )
    return {
        "exporter": "export_rag_corpus",
        "contract_id": "rag_corpus_contract",
        "package": str(package_path),
        "output": str(output_path),
        "row_count": len(rows),
        "granularity": granularity,
        "missing_source_link_count": missing,
        "contract_pass": bool(rows),
    }


def _bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--granularity", choices=["child", "parent", "all"], default="all"
    )
    parser.add_argument("--include-summary", type=_bool, default=True)
    parser.add_argument("--include-keywords", type=_bool, default=True)
    parser.add_argument("--min-chars", type=int, default=0)
    parser.add_argument("--fail-on-missing-source-links", type=_bool, default=False)
    args = parser.parse_args()
    try:
        result = export_rag_corpus(
            args.package,
            args.out,
            granularity=args.granularity,
            include_summary=args.include_summary,
            include_keywords=args.include_keywords,
            min_chars=args.min_chars,
            fail_on_missing_source_links=args.fail_on_missing_source_links,
        )
    except (PackageReadError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
