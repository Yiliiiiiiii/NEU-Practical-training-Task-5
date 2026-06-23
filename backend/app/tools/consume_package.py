import argparse
import json
import zipfile
from pathlib import Path

from app.verifiers.package_verifier import verify_package_zip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a SchemaPack package.")
    parser.add_argument("zip_path", type=Path)
    args = parser.parse_args(argv)

    report = verify_package_zip(args.zip_path)
    if not report.passed:
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 1

    with zipfile.ZipFile(args.zip_path) as archive:
        content = json.loads(archive.read("content.json"))
        chunks = json.loads(archive.read("chunks.json"))

    block_ids = {block["block_id"] for block in content.get("blocks", [])}
    linked_blocks = {
        block_id
        for chunk in chunks.get("chunks", [])
        for block_id in chunk.get("source_blocks", [])
        if block_id in block_ids
    }
    coverage = len(linked_blocks) / len(block_ids) if block_ids else 1.0
    result = {
        "doc_id": content.get("doc_id"),
        "task_id": content.get("task_id"),
        "content_field_count": len(content.get("data", {})),
        "chunk_count": len(chunks.get("chunks", [])),
        "source_block_coverage": coverage,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
