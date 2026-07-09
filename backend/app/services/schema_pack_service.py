from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SCHEMA_PACK_ROOT = Path(__file__).resolve().parents[3] / "schema_packs"


class SchemaPackService:
    def __init__(self, root: str | Path = DEFAULT_SCHEMA_PACK_ROOT) -> None:
        self.root = Path(root)

    def example_pack_dir(self, schema_pack_id: str) -> Path:
        return self.root / "examples" / schema_pack_id

    def load_json_asset(self, schema_pack_id: str, filename: str) -> dict[str, Any]:
        path = self.example_pack_dir(schema_pack_id) / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return payload

    def load_router_rules(self) -> dict[str, dict[str, Any]]:
        examples = self.root / "examples"
        if not examples.exists():
            return {}
        loaded: dict[str, dict[str, Any]] = {}
        for path in sorted(examples.glob("*/router_rules.yaml")):
            payload = self._read_simple_yaml(path)
            schema_id = str(payload.get("schema_id") or path.parent.name)
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

    @classmethod
    def _read_simple_yaml(cls, path: Path) -> dict[str, Any]:
        lines = path.read_text(encoding="utf-8").splitlines()
        root: dict[str, Any] = {}
        current_key: str | None = None
        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line.startswith(" ") and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value:
                    root[key] = cls._scalar(value)
                    current_key = None
                else:
                    root[key] = []
                    current_key = key
                continue
            if current_key is None:
                continue
            if stripped.startswith("- "):
                if not isinstance(root[current_key], list):
                    root[current_key] = []
                root[current_key].append(cls._scalar(stripped[2:].strip()))
                continue
            if ":" in stripped:
                if not isinstance(root[current_key], dict):
                    root[current_key] = {}
                key, value = stripped.split(":", 1)
                root[current_key][key.strip()] = cls._scalar(value.strip())
        return root

    @staticmethod
    def _scalar(value: str) -> Any:
        if value in {"true", "True"}:
            return True
        if value in {"false", "False"}:
            return False
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value.strip("\"'")
