"""Export structured fields from a SchemaPack package as CSV."""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from package_consumption import (  # noqa: E402
    PackageReadError,
    load_manifest,
    load_metadata,
    resolved_package_dir,
    validate_manifest_files,
)

FIELDNAMES = [
    "package_id",
    "task_id",
    "doc_id",
    "schema_id",
    "schema_version",
    "template_id",
    "template_version",
    "field_id",
    "field_name",
    "field_value",
    "field_type",
    "source_block_ids",
    "confidence",
    "review_required",
]


def _load_content(package_dir: Path) -> dict[str, Any]:
    for name in ("content.json", "canonical.json"):
        path = package_dir / name
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise PackageReadError(f"{name} is invalid: {exc}") from exc
            if isinstance(value, dict):
                return value
    raise PackageReadError("content.json or canonical.json is required")


def _flatten(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        rows: list[tuple[str, Any]] = []
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten(child, path))
        return rows
    if isinstance(value, list):
        return [(prefix, value)]
    return [(prefix, value)]


def _base_metadata(
    manifest: dict[str, Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    generator = manifest.get("generator", {})
    base = {
        "package_id": metadata.get("package_id") or manifest.get("package_id"),
        "task_id": metadata.get("task_id") or manifest.get("task_id"),
        "doc_id": metadata.get("doc_id") or manifest.get("doc_id"),
        "schema_id": metadata.get("schema_id") or generator.get("schema_id"),
        "schema_version": metadata.get("schema_version")
        or generator.get("schema_version"),
        "template_id": metadata.get("template_id") or generator.get("template_id"),
        "template_version": metadata.get("template_version")
        or generator.get("template_version"),
    }
    if not base["schema_id"] or not base["schema_version"]:
        raise PackageReadError("metadata schema_id and schema_version are required")
    return base


def export_structured_csv(
    package_path: Path,
    output_path: Path,
    *,
    mode: str = "long",
) -> dict[str, Any]:
    if mode not in {"long", "wide"}:
        raise ValueError("mode must be long or wide")
    with resolved_package_dir(package_path) as package_dir:
        manifest = load_manifest(package_dir)
        validate_manifest_files(package_dir, manifest)
        metadata = load_metadata(package_dir)
        content = _load_content(package_dir)
        base = _base_metadata(manifest, metadata)
    flattened = _flatten(content)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "wide":
        row = {**base, **{key: _csv_value(value) for key, value in flattened}}
        fieldnames = list(row)
        rows = [row]
    else:
        rows = [
            {
                **base,
                "field_id": field_id,
                "field_name": field_id.rsplit(".", 1)[-1],
                "field_value": _csv_value(value),
                "field_type": type(value).__name__,
                "source_block_ids": "",
                "confidence": "",
                "review_required": False,
            }
            for field_id, value in flattened
        ]
        fieldnames = FIELDNAMES
    if not rows:
        raise PackageReadError("structured export is empty")
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "exporter": "export_structured_csv",
        "contract_id": "structured_csv_contract",
        "package": str(package_path),
        "output": str(output_path),
        "row_count": len(rows),
        "mode": mode,
        "contract_pass": bool(rows),
    }


def _csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path)
    group.add_argument("--package-dir", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--mode", choices=["long", "wide"], default="long")
    args = parser.parse_args()
    try:
        result = export_structured_csv(
            args.package or args.package_dir, args.out, mode=args.mode
        )
    except (PackageReadError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
