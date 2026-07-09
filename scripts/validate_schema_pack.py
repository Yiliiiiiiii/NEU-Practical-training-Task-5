"""Validate a Topic 5 SchemaPack example directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.target_schema import TargetSchema  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_section: str | None = None
    current_alias: str | None = None
    current_list_item: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_section = key
            current_alias = None
            current_list_item = None
            if value:
                root[key] = _scalar(value)
            elif key in {"aliases", "defaults", "thresholds", "candidate_hints"}:
                root[key] = {}
            else:
                root[key] = []
            continue

        if current_section == "aliases":
            if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
                key, _value = stripped.split(":", 1)
                current_alias = key.strip()
                root.setdefault("aliases", {})[current_alias] = []
                continue
            if current_alias and stripped.startswith("- "):
                root["aliases"][current_alias].append(_scalar(stripped[2:]))
                continue

        if current_section in {"regex_rules", "negative_pairs", "transform_rules"}:
            if stripped.startswith("- "):
                key_value = stripped[2:].strip()
                current_list_item = {}
                root.setdefault(current_section, []).append(current_list_item)
                if ":" in key_value:
                    key, value = key_value.split(":", 1)
                    current_list_item[key.strip()] = _scalar(value)
                continue
            if current_list_item is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_list_item[key.strip()] = _scalar(value)
                continue

        if current_section in {"defaults", "thresholds"} and ":" in stripped:
            key, value = stripped.split(":", 1)
            root.setdefault(current_section, {})[key.strip()] = _scalar(value)

    return root


def validate_schema_pack(pack_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    schema_pack_id = pack_dir.name

    target_schema_path = pack_dir / "target_schema.json"
    metadata_template_path = pack_dir / "metadata_template.json"
    mapping_rules_path = pack_dir / "mapping_rules.yaml"
    content_org_path = pack_dir / "content_org.yaml"
    router_rules_path = pack_dir / "router_rules.yaml"

    for path in [
        target_schema_path,
        metadata_template_path,
        mapping_rules_path,
        content_org_path,
    ]:
        if not path.is_file():
            errors.append(f"{path.name} is missing")

    if not router_rules_path.is_file():
        warnings.append("router_rules.yaml is missing")

    if errors:
        return {
            "status": "failed",
            "schema_pack_id": schema_pack_id,
            "errors": errors,
            "warnings": warnings,
        }

    try:
        target_schema = TargetSchema.model_validate(_read_json(target_schema_path))
    except Exception as exc:  # pragma: no cover - exact pydantic details are unstable
        errors.append(f"target_schema.json is invalid: {exc}")
        target_schema = None

    try:
        metadata_template = _read_json(metadata_template_path)
    except Exception as exc:
        errors.append(f"metadata_template.json is invalid: {exc}")
        metadata_template = {}

    try:
        mapping_rules = _read_simple_yaml(mapping_rules_path)
    except Exception as exc:
        errors.append(f"mapping_rules.yaml is invalid: {exc}")
        mapping_rules = {}

    if target_schema is not None:
        schema_id = target_schema.schema_id
        if str(metadata_template.get("schema_id")) != schema_id:
            errors.append("metadata_template.schema_id does not match target_schema.schema_id")
        if str(mapping_rules.get("schema_id")) != schema_id:
            errors.append("mapping_rules.schema_id does not match target_schema.schema_id")

        template_id = str(metadata_template.get("template_id") or "")
        if not template_id:
            errors.append("metadata_template.template_id is missing")
        if str(mapping_rules.get("template_id") or "") != template_id:
            errors.append("mapping_rules.template_id does not match metadata_template.template_id")

        if not metadata_template.get("version"):
            errors.append("metadata_template.version is missing")
        for required_key in ["schema_id", "template_id", "version"]:
            if not mapping_rules.get(required_key):
                errors.append(f"mapping_rules.{required_key} is missing")

        aliases = mapping_rules.get("aliases", {})
        regex_targets = {
            str(item.get("target_field_id"))
            for item in mapping_rules.get("regex_rules", [])
            if isinstance(item, dict) and item.get("target_field_id")
        }
        for field in target_schema.fields:
            if not field.required:
                continue
            field_aliases = aliases.get(field.field_id, []) if isinstance(aliases, dict) else []
            if not field_aliases and field.field_id not in regex_targets:
                errors.append(
                    f"required field {field.field_id} has no alias or regex rule"
                )

    for index, item in enumerate(mapping_rules.get("negative_pairs", [])):
        if not isinstance(item, dict):
            errors.append(f"negative_pairs[{index}] must be an object")
            continue
        if not item.get("source_pattern") or not item.get("target_field_id"):
            errors.append(
                f"negative_pairs[{index}] requires source_pattern and target_field_id"
            )
        elif not re.compile(str(item["source_pattern"])):
            errors.append(f"negative_pairs[{index}].source_pattern is invalid")

    return {
        "status": "failed" if errors else "passed",
        "schema_pack_id": schema_pack_id,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema_pack_dir", type=Path)
    args = parser.parse_args()
    result = validate_schema_pack(args.schema_pack_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
