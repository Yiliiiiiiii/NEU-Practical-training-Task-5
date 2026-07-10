from __future__ import annotations

import json
from pathlib import Path
from typing import Any, overload

import yaml

from app.schemas.conversion_assertions import ConversionAssertionConfig
from app.schemas.schema_pack_contract import SchemaPackManifest
from app.services.schema_pack_contract_validator import SchemaPackContractValidator

DEFAULT_SCHEMA_PACK_ROOT = Path(__file__).resolve().parents[3] / "schema_packs"
CURRENT_SCHEMA_PACK_AGENT_VERSION = "1.0.0"
SUPPORTED_PACKAGE_CONTRACT_VERSION = "1.1"


class SchemaPackService:
    def __init__(self, root: str | Path = DEFAULT_SCHEMA_PACK_ROOT) -> None:
        self.root = Path(root).resolve()

    def example_pack_dir(self, schema_pack_id: str) -> Path:
        path = (self.root / "examples" / schema_pack_id).resolve()
        examples_root = (self.root / "examples").resolve()
        if examples_root != path and examples_root not in path.parents:
            raise ValueError("unsafe SchemaPack identifier")
        return path

    def load_manifest(self, schema_pack_id: str) -> SchemaPackManifest:
        path = self.example_pack_dir(schema_pack_id) / "schema_pack.yaml"
        payload = self._read_yaml(path)
        return SchemaPackManifest.model_validate(payload)

    def validate_for_execution(
        self,
        schema_pack_id: str,
        *,
        input_uir_version: str,
    ) -> SchemaPackManifest:
        report = SchemaPackContractValidator().validate(
            self.example_pack_dir(schema_pack_id)
        )
        if report["status"] != "passed":
            details = "; ".join(str(item) for item in report["errors"])
            raise ValueError(f"SchemaPack contract validation failed: {details}")

        manifest = self.load_manifest(schema_pack_id)
        compatibility = manifest.compatibility
        current = self._version_tuple(CURRENT_SCHEMA_PACK_AGENT_VERSION)
        if current < self._version_tuple(compatibility.min_agent_version):
            raise ValueError("SchemaPack requires a newer agent version")
        if (
            compatibility.max_agent_version is not None
            and current > self._version_tuple(compatibility.max_agent_version)
        ):
            raise ValueError("SchemaPack does not support the current agent version")
        if compatibility.input_uir_version != input_uir_version:
            raise ValueError(
                "SchemaPack input_uir_version does not match the selected document"
            )
        if (
            compatibility.package_contract_version
            != SUPPORTED_PACKAGE_CONTRACT_VERSION
        ):
            raise ValueError(
                "SchemaPack package_contract_version must be "
                f"{SUPPORTED_PACKAGE_CONTRACT_VERSION}"
            )
        return manifest

    def load_target_schema(self, schema_pack_id: str) -> dict[str, Any]:
        return self._load_json_manifest_asset(schema_pack_id, "target_schema")

    def load_metadata_template(self, schema_pack_id: str) -> dict[str, Any]:
        return self._load_json_manifest_asset(schema_pack_id, "metadata_template")

    def load_mapping_rules(self, schema_pack_id: str) -> dict[str, Any]:
        return self._load_yaml_manifest_asset(schema_pack_id, "mapping_rules")

    def load_content_org(self, schema_pack_id: str) -> dict[str, Any]:
        return self._load_yaml_manifest_asset(schema_pack_id, "content_org")

    def load_output_assertions(
        self,
        schema_pack_id: str,
    ) -> ConversionAssertionConfig | None:
        manifest = self.load_manifest(schema_pack_id)
        if manifest.assets.output_assertions is None:
            return None
        path = self._asset_path(schema_pack_id, manifest, "output_assertions")
        return ConversionAssertionConfig.model_validate(self._read_yaml(path))

    @overload
    def load_router_rules(self, schema_pack_id: str) -> dict[str, Any] | None: ...

    @overload
    def load_router_rules(self, schema_pack_id: None = None) -> dict[str, dict[str, Any]]: ...

    def load_router_rules(
        self,
        schema_pack_id: str | None = None,
    ) -> dict[str, Any] | dict[str, dict[str, Any]] | None:
        if schema_pack_id is not None:
            manifest = self.load_manifest(schema_pack_id)
            if manifest.assets.router_rules is None:
                return None
            return self._read_yaml(
                self._asset_path(schema_pack_id, manifest, "router_rules")
            )

        examples = self.root / "examples"
        if not examples.exists():
            return {}
        loaded: dict[str, dict[str, Any]] = {}
        for pack_dir in sorted(path for path in examples.iterdir() if path.is_dir()):
            manifest_path = pack_dir / "schema_pack.yaml"
            if not manifest_path.is_file():
                continue
            payload = self.load_router_rules(pack_dir.name)
            if not isinstance(payload, dict):
                continue
            schema_id = str(payload.get("schema_id") or pack_dir.name)
            template_id = str(payload.get("template_id") or f"{schema_id}_base_v1")
            loaded[schema_id] = {
                "template_id": template_id,
                "keywords": list(payload.get("keywords", [])),
                "field_labels": list(payload.get("field_labels", [])),
                "risks": dict(payload.get("risks", {})),
                "scoring": dict(payload.get("scoring", {})),
                "thresholds": dict(payload.get("thresholds", {})),
                "source": "schema_pack_router_rules",
            }
        return loaded

    def _load_json_manifest_asset(
        self,
        schema_pack_id: str,
        asset_name: str,
    ) -> dict[str, Any]:
        manifest = self.load_manifest(schema_pack_id)
        return self._read_json(self._asset_path(schema_pack_id, manifest, asset_name))

    def _load_yaml_manifest_asset(
        self,
        schema_pack_id: str,
        asset_name: str,
    ) -> dict[str, Any]:
        manifest = self.load_manifest(schema_pack_id)
        return self._read_yaml(self._asset_path(schema_pack_id, manifest, asset_name))

    def _asset_path(
        self,
        schema_pack_id: str,
        manifest: SchemaPackManifest,
        asset_name: str,
    ) -> Path:
        relative_path = getattr(manifest.assets, asset_name)
        if relative_path is None:
            raise FileNotFoundError(f"{asset_name} is not configured")
        pack_dir = self.example_pack_dir(schema_pack_id)
        resolved = (pack_dir / relative_path).resolve()
        if pack_dir != resolved and pack_dir not in resolved.parents:
            raise ValueError(f"unsafe SchemaPack asset path: {relative_path}")
        if not resolved.is_file():
            raise FileNotFoundError(f"SchemaPack asset is missing: {relative_path}")
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
    def _version_tuple(value: str) -> tuple[int, int, int]:
        return tuple(int(part) for part in value.split("."))
