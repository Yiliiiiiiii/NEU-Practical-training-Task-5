import re
from datetime import datetime
from typing import Any

from app.schemas.canonical import CanonicalField
from app.schemas.mapping import FieldMapping
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRDocument
from app.utils.ids import new_id

CHINESE_DATE_RE = re.compile(
    r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
)

FALLBACK_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y年%m月%d日",
    "%Y%m%d",
]


class TransformEngine:
    def execute(
        self,
        uir: UIRDocument,
        mappings: list[FieldMapping],
        transform_rules: list[TransformRule],
        enum_maps: dict[str, dict[str, str]],
        defaults: dict[str, object],
    ) -> tuple[dict[str, CanonicalField], list[dict[str, Any]]]:
        values: dict[str, Any] = {}
        trace_events: list[dict[str, Any]] = []
        errors: list[str] = []

        for mapping in mappings:
            if mapping.status != "confirmed":
                continue
            source_value = self._resolve_source(
                uir, mapping.source_field.source_path
            )
            values[mapping.target_field_id] = {
                "value": source_value,
                "type": self._infer_type(source_value),
                "candidate_id": mapping.candidate_id,
                "source_blocks": [],
            }

        for rule in transform_rules:
            try:
                self._apply_rule(rule, values, enum_maps, trace_events)
            except Exception as exc:
                errors.append(f"rule {rule.rule_id}: {exc}")
                trace_events.append({
                    "trace_id": new_id("trace"),
                    "stage": "field_transform",
                    "action": rule.operation,
                    "target_field_id": rule.target_field_id,
                    "status": "error",
                    "reason": str(exc),
                })

        for field_id, default_val in defaults.items():
            if field_id not in values or values[field_id].get("value") is None:
                values[field_id] = {
                    "value": default_val,
                    "type": self._infer_type(default_val),
                    "candidate_id": "",
                    "source_blocks": [],
                }
                trace_events.append({
                    "trace_id": new_id("trace"),
                    "stage": "field_transform",
                    "action": "default_value",
                    "target_field_id": field_id,
                    "source": {"value": None},
                    "result": {"value": default_val},
                    "status": "success",
                    "reason": "applied default value",
                })

        canonical_fields = {}
        for field_id, info in values.items():
            canonical_fields[field_id] = CanonicalField(
                value=info["value"],
                type=info.get("type", "string"),
                source_candidates=([info["candidate_id"]] if info.get("candidate_id") else []),
                source_blocks=info.get("source_blocks", []),
            )

        return canonical_fields, trace_events

    def _apply_rule(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        enum_maps: dict[str, dict[str, str]],
        trace_events: list[dict[str, Any]],
    ) -> None:
        operation = rule.operation
        if operation == "rename":
            self._rename(rule, values, trace_events)
        elif operation == "type_cast":
            self._type_cast(rule, values, trace_events)
        elif operation == "date_format":
            self._date_format(rule, values, trace_events)
        elif operation == "enum_map":
            self._enum_map(rule, values, enum_maps, trace_events)
        elif operation == "default":
            self._default(rule, values, trace_events)
        elif operation == "merge":
            self._merge(rule, values, trace_events)
        elif operation == "split":
            self._split(rule, values, trace_events)
        else:
            raise ValueError(f"unknown operation: {operation}")

    def _rename(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target:
            return
        source_value = self._get_value_from_source(rule.source_field, values)
        before = values.get(target, {}).get("value") if target in values else None
        values[target] = {
            "value": source_value,
            "type": self._infer_type(source_value),
            "candidate_id": "",
            "source_blocks": [],
        }
        trace_events.append({
            "trace_id": new_id("trace"),
            "stage": "field_transform",
            "action": "rename",
            "target_field_id": target,
            "source": {"path": rule.source_field, "value": before},
            "result": {"value": source_value},
            "rule_id": rule.rule_id,
            "reason": f"renamed from {rule.source_field}",
            "status": "success",
        })

    def _type_cast(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target or target not in values:
            return
        entry = values[target]
        source_val = entry["value"]
        cast_to = rule.params.get("to", "string")
        before = source_val
        result_val = self._cast_value(source_val, cast_to)
        entry["value"] = result_val
        entry["type"] = cast_to
        trace_events.append({
            "trace_id": new_id("trace"),
            "stage": "field_transform",
            "action": "type_cast",
            "target_field_id": target,
            "source": {"value": before},
            "result": {"value": result_val},
            "rule_id": rule.rule_id,
            "reason": f"cast to {cast_to}",
            "status": "success",
        })

    def _date_format(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target or target not in values:
            return
        entry = values[target]
        source_val = str(entry["value"]) if entry["value"] is not None else ""
        before = source_val
        output_format = rule.params.get("output_format", "YYYY-MM-DD")
        result_val = self._convert_date(source_val, output_format)
        entry["value"] = result_val
        entry["type"] = "date"
        trace_events.append({
            "trace_id": new_id("trace"),
            "stage": "field_transform",
            "action": "date_format",
            "target_field_id": target,
            "source": {"value": before},
            "result": {"value": result_val},
            "rule_id": rule.rule_id,
            "reason": f"date format conversion to {output_format}",
            "status": "success",
        })

    def _enum_map(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        enum_maps: dict[str, dict[str, str]],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target or target not in values:
            return
        entry = values[target]
        source_val = entry["value"]
        mapping = enum_maps.get(target, {})
        mapped_val = mapping.get(str(source_val), str(source_val))
        if str(source_val) not in mapping:
            trace_events.append({
                "trace_id": new_id("trace"),
                "stage": "field_transform",
                "action": "enum_map",
                "target_field_id": target,
                "source": {"value": source_val},
                "result": {"value": mapped_val},
                "rule_id": rule.rule_id,
                "reason": f"enum value '{source_val}' not in mapping, passed through",
                "status": "warning",
            })
        else:
            trace_events.append({
                "trace_id": new_id("trace"),
                "stage": "field_transform",
                "action": "enum_map",
                "target_field_id": target,
                "source": {"value": source_val},
                "result": {"value": mapped_val},
                "rule_id": rule.rule_id,
                "reason": "enum mapped",
                "status": "success",
            })
        entry["value"] = mapped_val

    def _default(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target:
            return
        default_val = rule.params.get("value")
        if target not in values or values[target].get("value") is None:
            values[target] = {
                "value": default_val,
                "type": self._infer_type(default_val),
                "candidate_id": "",
                "source_blocks": [],
            }
            trace_events.append({
                "trace_id": new_id("trace"),
                "stage": "field_transform",
                "action": "default_value",
                "target_field_id": target,
                "source": {"value": None},
                "result": {"value": default_val},
                "rule_id": rule.rule_id,
                "reason": "applied default value from rule",
                "status": "success",
            })

    def _merge(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        target = rule.target_field_id
        if not target:
            return
        separator = rule.params.get("separator", "")
        skip_empty = rule.params.get("skip_empty", True)
        parts = []
        for src in rule.source_fields:
            val = self._get_value_from_source(src, values)
            if skip_empty and (val is None or val == ""):
                continue
            parts.append(str(val) if val is not None else "")
        merged = separator.join(parts)
        before = values.get(target, {}).get("value") if target in values else None
        values[target] = {
            "value": merged,
            "type": "string",
            "candidate_id": "",
            "source_blocks": [],
        }
        trace_events.append({
            "trace_id": new_id("trace"),
            "stage": "field_transform",
            "action": "merge",
            "target_field_id": target,
            "source": {"fields": rule.source_fields, "value": before},
            "result": {"value": merged},
            "rule_id": rule.rule_id,
            "reason": f"merged {len(rule.source_fields)} fields",
            "status": "success",
        })

    def _split(
        self,
        rule: TransformRule,
        values: dict[str, Any],
        trace_events: list[dict[str, Any]],
    ) -> None:
        separator = rule.params.get("separator", "|")
        source_value = self._get_value_from_source(rule.source_field, values)
        before = source_value
        parts = str(source_value).split(separator) if source_value is not None else [""]
        targets = rule.target_fields or []
        for i, target_id in enumerate(targets):
            val = parts[i] if i < len(parts) else ""
            values[target_id] = {
                "value": val,
                "type": "string",
                "candidate_id": "",
                "source_blocks": [],
            }
        trace_events.append({
            "trace_id": new_id("trace"),
            "stage": "field_transform",
            "action": "split",
            "target_field_id": targets[0] if targets else None,
            "source": {"value": before},
            "result": {"value": parts},
            "rule_id": rule.rule_id,
            "reason": f"split into {len(targets)} fields",
            "status": "success",
        })

    def _resolve_source(self, uir: UIRDocument, source_path: str) -> Any:
        parts = source_path.split(".")
        if parts[0] == "metadata":
            key = ".".join(parts[1:])
            return uir.metadata.get(key)
        if parts[0] == "blocks" and len(parts) >= 3:
            block_id = parts[1]
            for block in uir.blocks:
                if block.block_id == block_id:
                    attr = ".".join(parts[2:])
                    if attr.startswith("attributes."):
                        return block.attributes.get(attr[len("attributes."):])
                    if attr == "text":
                        return block.text
        return None

    def _get_value_from_source(
        self, source_field: str, values: dict[str, Any]
    ) -> Any:
        if source_field in values:
            return values[source_field].get("value")
        parts = source_field.split(".")
        if parts[0] == "metadata":
            return values.get(".".join(parts[1:]), {}).get("value")
        return None

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            if re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}", value):
                return "date"
            return "string"
        return "string"

    @staticmethod
    def _cast_value(value: Any, to_type: str) -> Any:
        if value is None:
            return None
        if to_type == "string":
            return str(value)
        if to_type in ("integer", "int"):
            return int(float(str(value).replace(",", "")))
        if to_type == "float":
            return float(str(value).replace(",", ""))
        if to_type == "bool":
            return str(value).lower() in ("true", "1", "yes")
        if to_type == "date":
            return TransformEngine._convert_date(str(value))
        return value

    @staticmethod
    def _convert_date(value: str, output_format: str = "YYYY-MM-DD") -> str:
        match = CHINESE_DATE_RE.search(value)
        if match:
            y, m, d = match.group(1), match.group(2), match.group(3)
            return f"{y}-{int(m):02d}-{int(d):02d}"
        for fmt in FALLBACK_DATE_FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return value
