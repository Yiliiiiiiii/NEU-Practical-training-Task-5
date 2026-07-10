from __future__ import annotations

import json
import re
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.conversion_assertions import ConversionAssertionConfig
from app.schemas.mapping_template import MappingTemplate
from app.schemas.schema_pack_contract import SchemaPackManifest, validate_semver
from app.schemas.target_schema import TargetSchema
from app.schemas.topic5_convert import MetadataTemplateConfig

STANDARD_METADATA_FIELDS = {
    "document_id",
    "language",
    "publish_date",
    "retrieved_at",
    "source",
    "source_url",
}


class SchemaPackContractValidator:
    def validate(self, pack_dir: str | Path) -> dict[str, Any]:
        pack_path = Path(pack_dir).resolve()
        errors: list[str] = []
        warnings: list[str] = []
        validated_assets: list[str] = []
        schema_pack_id = pack_path.name
        schema_pack_version: str | None = None

        if not pack_path.is_dir():
            errors.append("SchemaPack directory is missing")
            return self._report(schema_pack_id, schema_pack_version, errors, warnings, [])

        manifest_path = pack_path / "schema_pack.yaml"
        if not manifest_path.is_file():
            errors.append("schema_pack.yaml is missing")
            return self._report(schema_pack_id, schema_pack_version, errors, warnings, [])

        try:
            manifest = SchemaPackManifest.model_validate(self._read_yaml(manifest_path))
            validated_assets.append("schema_pack.yaml")
            schema_pack_id = manifest.schema_pack_id
            schema_pack_version = manifest.schema_pack_version
        except Exception as exc:
            errors.append(f"schema_pack.yaml is invalid: {exc}")
            return self._report(schema_pack_id, schema_pack_version, errors, warnings, [])

        if manifest.schema_pack_id != pack_path.name:
            errors.append(
                "schema_pack.yaml.schema_pack_id does not match SchemaPack directory name"
            )

        loaded: dict[str, dict[str, Any]] = {}
        for asset_name, relative_path in manifest.assets.model_dump().items():
            if relative_path is None:
                continue
            try:
                path = self._safe_asset_path(pack_path, relative_path)
                if path.suffix == ".json":
                    loaded[asset_name] = self._read_json(path)
                elif path.suffix in {".yaml", ".yml"}:
                    loaded[asset_name] = self._read_yaml(path)
                else:
                    raise ValueError("unsupported asset file type")
                validated_assets.append(relative_path)
            except FileNotFoundError:
                errors.append(f"{relative_path} is missing")
            except Exception as exc:
                errors.append(f"schema_pack.yaml.assets.{asset_name}: {exc}")

        target_schema = self._validate_target_schema(loaded, errors)
        self._validate_metadata_template(loaded, errors)
        self._validate_content_org(loaded, errors)
        self._validate_router_rules(loaded, errors)
        assertions = self._validate_assertions(loaded, errors)
        self._validate_cross_file_ids(manifest, loaded, target_schema, assertions, errors)
        self._validate_mapping_contract(
            loaded.get("mapping_rules"),
            target_schema,
            errors,
            display_name=manifest.display_name,
        )
        self._validate_assertion_fields(loaded, target_schema, assertions, errors)
        self._validate_fixture_json(pack_path, errors)

        return self._report(
            schema_pack_id,
            schema_pack_version,
            errors,
            warnings,
            validated_assets,
        )

    @staticmethod
    def _validate_target_schema(
        loaded: dict[str, dict[str, Any]],
        errors: list[str],
    ) -> TargetSchema | None:
        payload = loaded.get("target_schema")
        if payload is None:
            return None
        try:
            return TargetSchema.model_validate(payload)
        except Exception as exc:
            errors.append(f"target_schema.json is invalid: {exc}")
            return None

    @staticmethod
    def _validate_assertions(
        loaded: dict[str, dict[str, Any]],
        errors: list[str],
    ) -> ConversionAssertionConfig | None:
        payload = loaded.get("output_assertions")
        if payload is None:
            return None
        try:
            return ConversionAssertionConfig.model_validate(payload)
        except Exception as exc:
            errors.append(f"output_assertions.yaml is invalid: {exc}")
            return None

    @staticmethod
    def _validate_metadata_template(
        loaded: dict[str, dict[str, Any]],
        errors: list[str],
    ) -> None:
        payload = loaded.get("metadata_template")
        if payload is None:
            return
        try:
            template = MetadataTemplateConfig.model_validate(payload, strict=True)
            validate_semver(template.version)
        except Exception as exc:
            errors.append(f"metadata_template.json is invalid: {exc}")
            return

        seen: set[str] = set()
        for index, item in enumerate(template.metadata_fields):
            field_id = item.get("field_id") if isinstance(item, dict) else None
            if not isinstance(field_id, str) or not field_id.strip():
                errors.append(
                    f"metadata_template.json.metadata_fields[{index}].field_id is missing"
                )
                continue
            if field_id in seen:
                errors.append(
                    "metadata_template.json.metadata_fields contains duplicate field_id "
                    f"{field_id}"
                )
            seen.add(field_id)
            if "required" in item and not isinstance(item["required"], bool):
                errors.append(
                    f"metadata_template.json.metadata_fields[{index}].required "
                    "must be boolean"
                )

    @staticmethod
    def _validate_content_org(
        loaded: dict[str, dict[str, Any]],
        errors: list[str],
    ) -> None:
        payload = loaded.get("content_org")
        if payload is None:
            return
        contract_payload = dict(payload)
        contract_payload.pop("schema_id", None)
        try:
            ContentOrganizationOptions.model_validate(
                contract_payload,
                strict=True,
            )
        except Exception as exc:
            errors.append(f"content_org.yaml is invalid: {exc}")

    @staticmethod
    def _validate_router_rules(
        loaded: dict[str, dict[str, Any]],
        errors: list[str],
    ) -> None:
        payload = loaded.get("router_rules")
        if payload is None:
            return
        allowed = {
            "schema_id",
            "template_id",
            "version",
            "keywords",
            "field_labels",
            "risks",
            "scoring",
            "thresholds",
        }
        for name in sorted(str(key) for key in payload if key not in allowed):
            errors.append(f"router_rules.yaml.{name} is unsupported")
        for name in ("schema_id", "template_id"):
            if name in payload and not isinstance(payload[name], str):
                errors.append(f"router_rules.yaml.{name} must be a string")
        if "version" in payload:
            try:
                validate_semver(payload["version"])
            except Exception as exc:
                errors.append(f"router_rules.yaml.version is invalid: {exc}")
        for name in ("keywords", "field_labels"):
            value = payload.get(name, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                errors.append(f"router_rules.yaml.{name} must be an array of strings")
        for name in ("risks", "scoring", "thresholds"):
            if name in payload and not isinstance(payload[name], dict):
                errors.append(f"router_rules.yaml.{name} must be an object")

    @staticmethod
    def _validate_cross_file_ids(
        manifest: SchemaPackManifest,
        loaded: dict[str, dict[str, Any]],
        target_schema: TargetSchema | None,
        assertions: ConversionAssertionConfig | None,
        errors: list[str],
    ) -> None:
        schema_id = manifest.schema_pack_id
        if target_schema is not None and target_schema.schema_id != schema_id:
            errors.append("target_schema.json.schema_id does not match schema_pack_id")
        for asset_name in ("metadata_template", "mapping_rules", "content_org", "router_rules"):
            payload = loaded.get(asset_name)
            if payload and payload.get("schema_id") not in {None, schema_id}:
                errors.append(f"{asset_name}.schema_id does not match schema_pack_id")
        if assertions is not None and assertions.schema_id != schema_id:
            errors.append("output_assertions.yaml.schema_id does not match schema_pack_id")

        metadata = loaded.get("metadata_template", {})
        mapping = loaded.get("mapping_rules", {})
        router = loaded.get("router_rules", {})
        template_id = metadata.get("template_id")
        if template_id and mapping and mapping.get("template_id") != template_id:
            errors.append(
                "mapping_rules.yaml.template_id does not match metadata_template.template_id"
            )
        if template_id and router.get("template_id") not in {None, template_id}:
            errors.append(
                "router_rules.yaml.template_id does not match metadata_template.template_id"
            )
        template_version = metadata.get("version")
        if template_version and mapping.get("version") != template_version:
            errors.append(
                "mapping_rules.yaml.version does not match metadata_template.version"
            )
        if template_version and router.get("version") not in {None, template_version}:
            errors.append(
                "router_rules.yaml.version does not match metadata_template.version"
            )

    @staticmethod
    def _validate_mapping_contract(
        mapping: dict[str, Any] | None,
        target_schema: TargetSchema | None,
        errors: list[str],
        *,
        display_name: str,
    ) -> None:
        if mapping is None:
            return
        allowed = {
            "schema_id",
            "template_id",
            "name",
            "version",
            "aliases",
            "regex_rules",
            "negative_pairs",
            "transform_rules",
            "defaults",
            "enum_maps",
            "thresholds",
            "candidate_hints",
        }
        for name in sorted(str(key) for key in mapping if key not in allowed):
            errors.append(f"mapping_rules.yaml.{name} is unsupported")
        missing_required = False
        for required_key in ("schema_id", "template_id", "version"):
            if not mapping.get(required_key):
                errors.append(f"mapping_rules.yaml.{required_key} is missing")
                missing_required = True
        if not missing_required:
            regex_rules = [
                {
                    key: item[key]
                    for key in ("target_field_id", "pattern", "group")
                    if key in item
                }
                for item in mapping.get("regex_rules", [])
                if isinstance(item, dict)
            ]
            try:
                validate_semver(str(mapping["version"]))
                MappingTemplate.model_validate(
                    {
                        "template_id": mapping["template_id"],
                        "schema_id": mapping["schema_id"],
                        "name": mapping.get("name") or display_name,
                        "version": mapping["version"],
                        "aliases": mapping.get("aliases", {}),
                        "regex_rules": regex_rules,
                        "transform_rules": mapping.get("transform_rules", []),
                        "defaults": mapping.get("defaults", {}),
                        "enum_maps": mapping.get("enum_maps", {}),
                    },
                    strict=True,
                )
            except Exception as exc:
                errors.append(f"mapping_rules.yaml is invalid: {exc}")
        valid_fields = (
            {field.field_id for field in target_schema.fields}
            if target_schema
            else set()
        )
        aliases = mapping.get("aliases", {})
        if not isinstance(aliases, dict):
            errors.append("mapping_rules.yaml.aliases must be an object")
        else:
            for target_field_id in aliases:
                if valid_fields and target_field_id not in valid_fields:
                    errors.append(
                        f"mapping_rules.yaml.aliases.{target_field_id} "
                        "references unknown target field"
                    )
        for collection in ("defaults", "enum_maps"):
            values = mapping.get(collection, {})
            if not isinstance(values, dict):
                errors.append(f"mapping_rules.yaml.{collection} must be an object")
                continue
            for target_field_id in values:
                if valid_fields and target_field_id not in valid_fields:
                    errors.append(
                        f"mapping_rules.yaml.{collection}.{target_field_id} "
                        "references unknown target field"
                    )
        for collection in ("thresholds", "candidate_hints"):
            if collection in mapping and not isinstance(mapping[collection], dict):
                errors.append(f"mapping_rules.yaml.{collection} must be an object")
        thresholds = mapping.get("thresholds", {})
        if isinstance(thresholds, dict):
            allowed_thresholds = {"auto_accept", "review_required"}
            for name in sorted(
                str(key) for key in thresholds if key not in allowed_thresholds
            ):
                errors.append(f"mapping_rules.yaml.thresholds.{name} is unsupported")
            for name, value in thresholds.items():
                if (
                    not isinstance(value, int | float)
                    or isinstance(value, bool)
                    or not isfinite(float(value))
                ):
                    errors.append(
                        f"mapping_rules.yaml.thresholds.{name} must be a finite number"
                    )
                elif not 0.0 <= float(value) <= 1.0:
                    errors.append(
                        f"mapping_rules.yaml.thresholds.{name} must be between 0 and 1"
                    )
            auto_accept = thresholds.get("auto_accept")
            review_required = thresholds.get("review_required")
            if (
                isinstance(auto_accept, int | float)
                and not isinstance(auto_accept, bool)
                and isfinite(float(auto_accept))
                and isinstance(review_required, int | float)
                and not isinstance(review_required, bool)
                and isfinite(float(review_required))
                and review_required > auto_accept
            ):
                errors.append(
                    "mapping_rules.yaml.thresholds.review_required cannot exceed "
                    "auto_accept"
                )
        regex_collections = (
            ("regex_rules", "pattern"),
            ("negative_pairs", "source_pattern"),
        )
        for collection, pattern_key in regex_collections:
            items = mapping.get(collection, [])
            if not isinstance(items, list):
                errors.append(f"mapping_rules.yaml.{collection} must be an array")
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"mapping_rules.yaml.{collection}[{index}] must be an object")
                    continue
                target = item.get("target_field_id")
                if not isinstance(target, str) or not target:
                    errors.append(
                        f"mapping_rules.yaml.{collection}[{index}].target_field_id "
                        "is missing"
                    )
                elif valid_fields and target not in valid_fields:
                    errors.append(
                        f"mapping_rules.yaml.{collection}[{index}].target_field_id "
                        "references unknown target field"
                    )
                pattern = item.get(pattern_key)
                if not isinstance(pattern, str) or not pattern:
                    errors.append(
                        f"mapping_rules.yaml.{collection}[{index}].{pattern_key} is missing"
                    )
                    continue
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(
                        f"mapping_rules.yaml.{collection}[{index}].{pattern_key} is invalid: {exc}"
                    )

        transform_rules = mapping.get("transform_rules", [])
        if not isinstance(transform_rules, list):
            errors.append("mapping_rules.yaml.transform_rules must be an array")
        else:
            for index, item in enumerate(transform_rules):
                if not isinstance(item, dict):
                    errors.append(
                        f"mapping_rules.yaml.transform_rules[{index}] must be an object"
                    )
                    continue
                target_fields = item.get("target_fields", [])
                target_fields = target_fields if isinstance(target_fields, list) else []
                targets = [item.get("target_field_id"), *target_fields]
                for target in targets:
                    if target is not None and not isinstance(target, str):
                        errors.append(
                            f"mapping_rules.yaml.transform_rules[{index}] "
                            "target field references must be strings"
                        )
                    elif target is not None and valid_fields and target not in valid_fields:
                        errors.append(
                            f"mapping_rules.yaml.transform_rules[{index}] "
                            f"references unknown target field {target}"
                        )

        if target_schema is not None and isinstance(aliases, dict):
            regex_targets = {
                item.get("target_field_id")
                for item in mapping.get("regex_rules", [])
                if isinstance(item, dict)
                and isinstance(item.get("target_field_id"), str)
            }
            for field in target_schema.fields:
                if (
                    field.required
                    and not aliases.get(field.field_id)
                    and field.field_id not in regex_targets
                ):
                    errors.append(
                        f"required field {field.field_id} has no alias or regex rule"
                    )

    @staticmethod
    def _validate_assertion_fields(
        loaded: dict[str, dict[str, Any]],
        target_schema: TargetSchema | None,
        assertions: ConversionAssertionConfig | None,
        errors: list[str],
    ) -> None:
        if target_schema is None or assertions is None:
            return
        data_fields = {field.field_id for field in target_schema.fields}
        metadata_fields = set(STANDARD_METADATA_FIELDS)
        for item in loaded.get("metadata_template", {}).get("metadata_fields", []):
            if isinstance(item, dict) and item.get("field_id"):
                metadata_fields.add(str(item["field_id"]))
        for index, definition in enumerate(assertions.assertions):
            for name, path in (
                ("path", definition.path),
                ("parameters.other_path", definition.parameters.get("other_path")),
            ):
                if not isinstance(path, str):
                    continue
                if path.startswith("$.data."):
                    field_id = path.removeprefix("$.data.").split(".", 1)[0].split("[", 1)[0]
                    if field_id not in data_fields:
                        errors.append(
                            f"output_assertions.yaml.assertions[{index}].{name} "
                            f"references unknown target field {field_id}"
                        )
                if path.startswith("$.metadata."):
                    field_id = path.removeprefix("$.metadata.").split(".", 1)[0].split("[", 1)[0]
                    if field_id not in metadata_fields:
                        errors.append(
                            f"output_assertions.yaml.assertions[{index}].{name} "
                            f"references unknown metadata field {field_id}"
                        )

    @staticmethod
    def _validate_fixture_json(pack_path: Path, errors: list[str]) -> None:
        for directory_name in ("examples", "badcases"):
            directory = pack_path / directory_name
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    errors.append(f"{directory_name}/{path.name} is invalid: {exc}")

    @staticmethod
    def _safe_asset_path(pack_path: Path, relative_path: str) -> Path:
        resolved = (pack_path / relative_path).resolve()
        if pack_path != resolved and pack_path not in resolved.parents:
            raise ValueError(f"unsafe asset path: {relative_path}")
        if not resolved.is_file():
            raise FileNotFoundError(f"asset is missing: {relative_path}")
        return resolved

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        return payload

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name} must contain a YAML object")
        return payload

    @staticmethod
    def _report(
        schema_pack_id: str,
        schema_pack_version: str | None,
        errors: list[str],
        warnings: list[str],
        validated_assets: list[str],
    ) -> dict[str, Any]:
        return {
            "status": "failed" if errors else "passed",
            "schema_pack_id": schema_pack_id,
            "schema_pack_version": schema_pack_version,
            "errors": errors,
            "warnings": warnings,
            "validated_assets": sorted(validated_assets),
        }
