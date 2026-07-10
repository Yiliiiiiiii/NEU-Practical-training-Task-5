from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.schemas.metadata_template import (
    MetadataFieldConfig,
    MetadataFieldTrace,
    MetadataRenderResult,
    MetadataTemplateConfig,
    MetadataTemplateIssue,
    MetadataTemplateReport,
    MetadataValueSource,
)
from app.schemas.uir import UIRDocument

_MISSING = object()


class MetadataTemplateService:
    def render(
        self,
        *,
        uir: UIRDocument,
        transformed_fields: dict[str, Any],
        template: MetadataTemplateConfig,
        system_context: dict[str, Any],
    ) -> MetadataRenderResult:
        document_metadata: dict[str, Any] = {}
        traces: list[MetadataFieldTrace] = []
        issues: list[MetadataTemplateIssue] = []
        defaults_used: list[str] = []
        missing_required: list[str] = []

        for field in template.metadata_fields:
            value, source = self._resolve(
                field=field,
                uir=uir,
                transformed_fields=transformed_fields,
                system_context=system_context,
            )
            path = f"document_metadata.{field.field_id}"
            default_used = source.kind == "default"
            if default_used:
                defaults_used.append(field.field_id)

            if value is _MISSING or (value is None and field.required):
                if field.required:
                    missing_required.append(field.field_id)
                    issues.append(
                        MetadataTemplateIssue(
                            path=path,
                            error_code="metadata_required_missing",
                            message="Required document metadata field is missing.",
                            field_id=field.field_id,
                            expected_type=field.type,
                            actual_type="null" if value is None else "missing",
                        )
                    )
                traces.append(
                    MetadataFieldTrace(
                        field_id=field.field_id,
                        path=path,
                        source=source,
                        resolved=False,
                        default_used=default_used,
                        value_type="null" if value is None else None,
                    )
                )
                continue

            value_type = self._value_type(value)
            if self._is_empty(value) and not field.allow_empty:
                issues.append(
                    MetadataTemplateIssue(
                        path=path,
                        error_code="metadata_empty_not_allowed",
                        message="Document metadata field does not allow an empty value.",
                        field_id=field.field_id,
                        expected_type=field.type,
                        actual_type=value_type,
                    )
                )
                traces.append(
                    MetadataFieldTrace(
                        field_id=field.field_id,
                        path=path,
                        source=source,
                        resolved=False,
                        default_used=default_used,
                        value_type=value_type,
                    )
                )
                continue

            if not self._matches_type(value, field):
                issues.append(
                    MetadataTemplateIssue(
                        path=path,
                        error_code="metadata_type_mismatch",
                        message="Document metadata field has the wrong type.",
                        field_id=field.field_id,
                        expected_type=field.type,
                        actual_type=value_type,
                    )
                )
                traces.append(
                    MetadataFieldTrace(
                        field_id=field.field_id,
                        path=path,
                        source=source,
                        resolved=False,
                        default_used=default_used,
                        value_type=value_type,
                    )
                )
                continue

            document_metadata[field.field_id] = value
            traces.append(
                MetadataFieldTrace(
                    field_id=field.field_id,
                    path=path,
                    source=source,
                    resolved=True,
                    default_used=default_used,
                    value_type=value_type,
                )
            )

        report = MetadataTemplateReport(
            template_id=template.template_id,
            schema_id=template.schema_id,
            version=template.version,
            passed=not issues,
            field_traces=traces,
            defaults_used=defaults_used,
            missing_required_fields=missing_required,
            issues=issues,
        )
        return MetadataRenderResult(document_metadata=document_metadata, report=report)

    def _resolve(
        self,
        *,
        field: MetadataFieldConfig,
        uir: UIRDocument,
        transformed_fields: dict[str, Any],
        system_context: dict[str, Any],
    ) -> tuple[Any, MetadataValueSource]:
        if field.source_path is not None:
            value = self._resolve_path(
                field.source_path,
                uir=uir,
                transformed_fields=transformed_fields,
                system_context=system_context,
            )
            if value is not _MISSING:
                kind = (
                    "uir_metadata"
                    if field.source_path.startswith("uir.metadata.")
                    else "transformed_field"
                    if field.source_path.startswith("transformed_fields.")
                    else "system"
                )
                return value, MetadataValueSource(kind=kind, path=field.source_path)
        else:
            if field.field_id in uir.metadata:
                path = f"uir.metadata.{field.field_id}"
                return uir.metadata[field.field_id], MetadataValueSource(
                    kind="uir_metadata", path=path
                )
            if field.field_id in transformed_fields:
                path = f"transformed_fields.{field.field_id}"
                return transformed_fields[field.field_id], MetadataValueSource(
                    kind="transformed_field", path=path
                )

        if "default" in field.model_fields_set:
            return field.default, MetadataValueSource(kind="default", path=None)
        return _MISSING, MetadataValueSource(kind="missing", path=field.source_path)

    @staticmethod
    def _resolve_path(
        path: str,
        *,
        uir: UIRDocument,
        transformed_fields: dict[str, Any],
        system_context: dict[str, Any],
    ) -> Any:
        if path.startswith("uir.metadata."):
            value: Any = uir.metadata
            parts = path.removeprefix("uir.metadata.").split(".")
        elif path.startswith("transformed_fields."):
            value = transformed_fields
            parts = path.removeprefix("transformed_fields.").split(".")
        else:
            value = system_context
            parts = path.removeprefix("system.").split(".")
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return _MISSING
            value = value[part]
        return value

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}

    @staticmethod
    def _matches_type(value: Any, field: MetadataFieldConfig) -> bool:
        if field.type == "any" or (field.allow_empty and MetadataTemplateService._is_empty(value)):
            return True
        if field.type == "string":
            return isinstance(value, str)
        if field.type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if field.type == "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        if field.type == "boolean":
            return isinstance(value, bool)
        if field.type == "array":
            return isinstance(value, list)
        if field.type == "object":
            return isinstance(value, dict)
        if field.type == "date":
            if isinstance(value, date) and not isinstance(value, datetime):
                return True
            if isinstance(value, str):
                try:
                    date.fromisoformat(value)
                except ValueError:
                    return False
                return True
            return False
        if field.type == "datetime":
            if isinstance(value, datetime):
                return True
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    return False
                return True
            return False
        return False

    @staticmethod
    def _value_type(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, datetime):
            return "datetime"
        if isinstance(value, date):
            return "date"
        return type(value).__name__
