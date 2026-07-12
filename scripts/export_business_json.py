"""Export deterministic flat business JSON from a verified Topic 5 package."""

from __future__ import annotations

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
    load_chunks,
    load_manifest,
    load_metadata,
    resolved_package_dir,
    validate_manifest_files,
    validate_verified_package,
)


def export_business_json(package_path: Path, output_path: Path) -> dict[str, Any]:
    with resolved_package_dir(package_path) as package_dir:
        manifest = load_manifest(package_dir)
        validate_manifest_files(package_dir, manifest)
        validate_verified_package(package_dir, manifest)
        metadata = load_metadata(package_dir)
        content_path = package_dir / "content.json"
        if not content_path.is_file():
            raise PackageReadError("content.json is required")
        content = json.loads(content_path.read_text(encoding="utf-8"))
        if not isinstance(content, dict):
            raise PackageReadError("content.json must contain an object")
        chunks = load_chunks(package_dir)
    generator = manifest.get("generator", {})
    fields = content.get("data", content)
    if not isinstance(fields, dict):
        raise PackageReadError("business data must contain an object")
    source_links = sorted(
        {
            json.dumps(link, ensure_ascii=False, sort_keys=True)
            for chunk in chunks
            for link in chunk.get("source_links", [])
            if isinstance(link, dict)
        }
    )
    entity_tags = sorted(
        {
            json.dumps(tag, ensure_ascii=False, sort_keys=True)
            for chunk in chunks
            for tag in chunk.get("entity_tags", [])
            if isinstance(tag, dict)
        }
    )
    payload = {
        "doc_id": metadata.get("doc_id") or manifest.get("doc_id"),
        "schema_id": metadata.get("schema_id") or generator.get("schema_id"),
        "schema_version": metadata.get("schema_version")
        or generator.get("schema_version"),
        "template_id": metadata.get("template_id") or generator.get("template_id"),
        "template_version": metadata.get("template_version")
        or generator.get("template_version"),
        "document_metadata": content.get("document_metadata", {}),
        "fields": fields,
        "source_links": [json.loads(item) for item in source_links],
        "entity_tags": [json.loads(item) for item in entity_tags],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "exporter": "export_business_json",
        "contract_id": "flat_business_json_contract",
        "package": str(package_path),
        "output": str(output_path),
        "field_count": len(fields),
        "source_link_count": len(source_links),
        "entity_tag_count": len(entity_tags),
        "contract_pass": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = export_business_json(args.package, args.out)
    except (PackageReadError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
