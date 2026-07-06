"""Export SchemaPack package chunks as downstream training-corpus JSONL."""

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
    filter_chunks_by_granularity,
    read_validated_package,
    training_metadata,
)


def export_training_corpus(
    package_path: Path,
    output_path: Path,
    granularity: str = "all",
) -> dict[str, Any]:
    try:
        manifest, chunks = read_validated_package(package_path)
    except PackageReadError as exc:
        raise SystemExit(str(exc)) from exc
    chunks = filter_chunks_by_granularity(chunks, granularity)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "id": chunk.get("chunk_id") or f"chunk_{index:04d}",
            "text": chunk.get("text", ""),
            "metadata": training_metadata(manifest, chunk),
        }
        for index, chunk in enumerate(chunks)
    ]
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + "\n",
        encoding="utf-8",
    )
    return {
        "exporter": "export_training_corpus",
        "contract_id": "training_corpus_contract",
        "package": str(package_path),
        "output": str(output_path),
        "row_count": len(rows),
        "granularity": granularity,
        "schema_id": manifest.get("generator", {}).get("schema_id"),
        "template_id": manifest.get("generator", {}).get("template_id"),
        "contract_pass": bool(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package", required=True, type=Path, help="Package zip or directory."
    )
    parser.add_argument("--out", required=True, type=Path, help="Output JSONL path.")
    parser.add_argument(
        "--granularity",
        choices=["child", "parent", "all"],
        default="all",
        help="Filter chunks by granularity before export.",
    )
    args = parser.parse_args()

    result = export_training_corpus(
        args.package, args.out, granularity=args.granularity
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
