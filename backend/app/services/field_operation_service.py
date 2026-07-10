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
        "normalize_date",
        "normalize_datetime",
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
            return FieldOperationOutcome(applied=True, value=rule.params.get("value"))

        paths = rule.source_fields or ([rule.source_field] if rule.source_field else [])
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
            values = [str(value) for value in source_values if value is not None]
            if skip_empty:
                values = [value for value in values if value.strip()]
            return FieldOperationOutcome(applied=True, value=separator.join(values))

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
            return FieldOperationOutcome(
                applied=True,
                value=[item.strip() for item in re.split(pattern, value) if item.strip()],
            )
        if operation == "trim":
            if not isinstance(value, str):
                return FieldOperationOutcome(applied=False, error="source_type_invalid")
            return FieldOperationOutcome(applied=True, value=value.strip())
        if operation == "enum_map":
            mapping = rule.params.get("map", {})
            if not isinstance(mapping, dict):
                return FieldOperationOutcome(applied=False, error="parameters_invalid")
            if value not in mapping:
                return FieldOperationOutcome(applied=False, error="enum_value_unmapped")
            return FieldOperationOutcome(applied=True, value=mapping[value])
        if operation in {"normalize_date", "date_format", "normalize_datetime"}:
            from app.services.transform_service import TransformService

            normalized, issue = TransformService()._coerce_value(value, target_field, {})
            return FieldOperationOutcome(
                applied=issue is None,
                value=normalized,
                error=str(issue.get("code")) if issue else None,
            )
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
