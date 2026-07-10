from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.target_schema import TargetField
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRDocument


@dataclass(frozen=True)
class FieldOperationOutcome:
    applied: bool
    value: Any = None
    error: str | None = None


class FieldOperationService:
    SUPPORTED_OPERATIONS = {
        "date_format",
        "default",
        "enum_map",
        "merge",
        "normalize_boolean",
        "normalize_date",
        "normalize_datetime",
        "normalize_number",
        "rename",
        "split",
        "trim",
    }
    SAFE_METADATA_PATH = re.compile(r"^metadata(?:\.[A-Za-z0-9_\u4e00-\u9fff-]+)+$")
    SAFE_BLOCK_PATH = re.compile(r"^blocks\.([A-Za-z0-9_-]+)\.text$")

    def apply(
        self,
        *,
        rule: TransformRule,
        uir: UIRDocument,
        target_field: TargetField,
        current_value: Any,
    ) -> FieldOperationOutcome:
        operation = rule.operation
        if operation not in self.SUPPORTED_OPERATIONS:
            return FieldOperationOutcome(applied=False, error="unsupported_operation")

        if operation == "default":
            if current_value is not None:
                return FieldOperationOutcome(applied=False, value=current_value)
            return self._success(rule.params.get("value"), target_field)

        paths = rule.source_fields or ([rule.source_field] if rule.source_field else [])
        if len(paths) != len(set(paths)):
            return FieldOperationOutcome(
                applied=False, error="duplicate_source_path"
            )
        if not paths:
            source_values = [current_value]
        else:
            source_values = []
            for path in paths:
                resolved = self._resolve_source(uir, path)
                if resolved.error:
                    return resolved
                source_values.append(resolved.value)

        if operation == "merge":
            separator = str(rule.params.get("separator", "\n"))
            skip_empty = bool(rule.params.get("skip_empty", True))
            if any(
                value is not None and not isinstance(value, str)
                for value in source_values
            ):
                return FieldOperationOutcome(
                    applied=False, error="unsafe_implicit_coercion"
                )
            values = [value for value in source_values if isinstance(value, str)]
            if skip_empty:
                values = [value for value in values if value.strip()]
            return self._success(separator.join(values), target_field)

        value = source_values[0] if source_values else current_value
        if operation == "split":
            if not isinstance(value, str):
                return FieldOperationOutcome(applied=False, error="source_type_invalid")
            separators = rule.params.get("separators", ["、", ",", "，", ";", "；", "\n"])
            if not isinstance(separators, list) or not all(
                isinstance(item, str) and item for item in separators
            ):
                return FieldOperationOutcome(applied=False, error="parameters_invalid")
            pattern = "|".join(re.escape(item) for item in separators)
            return self._success(
                [item.strip() for item in re.split(pattern, value) if item.strip()],
                target_field,
            )
        if operation == "trim":
            if not isinstance(value, str):
                return FieldOperationOutcome(applied=False, error="source_type_invalid")
            return self._success(value.strip(), target_field)
        if operation == "enum_map":
            mapping = rule.params.get("map", {})
            if not isinstance(mapping, dict):
                return FieldOperationOutcome(applied=False, error="parameters_invalid")
            if value not in mapping:
                return FieldOperationOutcome(applied=False, error="enum_value_unmapped")
            return self._success(mapping[value], target_field)
        if operation == "normalize_boolean":
            normalized = self._normalize_boolean(value)
            if normalized is None:
                return FieldOperationOutcome(
                    applied=False, error="boolean_format_error"
                )
            return self._success(normalized, target_field)
        if operation in {
            "normalize_date",
            "date_format",
            "normalize_datetime",
            "normalize_number",
        }:
            from app.services.transform_service import TransformService

            normalized, issue = TransformService()._coerce_value(value, target_field, {})
            if issue:
                return FieldOperationOutcome(
                    applied=False, value=normalized, error=str(issue.get("code"))
                )
            return self._success(normalized, target_field)
        return self._success(value, target_field)

    @staticmethod
    def _normalize_boolean(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "1"}:
                return True
            if normalized in {"false", "no", "0"}:
                return False
        return None

    @staticmethod
    def _success(value: Any, target_field: TargetField) -> FieldOperationOutcome:
        matches = {
            "any": True,
            "string": isinstance(value, str),
            "text": isinstance(value, str),
            "enum": isinstance(value, str),
            "date": isinstance(value, str),
            "datetime": isinstance(value, str),
            "number": isinstance(value, int | float) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "object": isinstance(value, dict),
        }.get(
            target_field.type,
            isinstance(value, list) if target_field.type.startswith("array") else True,
        )
        if not matches:
            return FieldOperationOutcome(applied=False, error="target_type_invalid")
        return FieldOperationOutcome(applied=True, value=value)

    def _resolve_source(
        self, uir: UIRDocument, source_path: str
    ) -> FieldOperationOutcome:
        if self.SAFE_METADATA_PATH.fullmatch(source_path):
            if any(part.startswith("_") for part in source_path.split(".")[1:]):
                return FieldOperationOutcome(
                    applied=False, error="unsafe_source_path"
                )
            value: Any = uir.metadata
            for part in source_path.split(".")[1:]:
                if not isinstance(value, dict) or part not in value:
                    return FieldOperationOutcome(applied=False, error="source_missing")
                value = value[part]
            return FieldOperationOutcome(applied=True, value=value)
        block_match = self.SAFE_BLOCK_PATH.fullmatch(source_path)
        if block_match:
            block_id = block_match.group(1)
            block = next((item for item in uir.blocks if item.block_id == block_id), None)
            if block is None:
                return FieldOperationOutcome(applied=False, error="source_missing")
            return FieldOperationOutcome(applied=True, value=block.text)
        return FieldOperationOutcome(applied=False, error="unsafe_source_path")
