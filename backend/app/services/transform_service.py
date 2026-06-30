import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument


@dataclass(frozen=True)
class TransformResult:
    data: dict[str, Any]
    report: dict[str, Any]


class TransformService:
    def transform(
        self,
        task_id: str,
        uir: UIRDocument,
        schema: TargetSchema,
        template: MappingTemplate,
        mapping_report: MappingReport,
    ) -> TransformResult:
        data: dict[str, Any] = {}
        traces: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        fields_by_id = {field.field_id: field for field in schema.fields}

        for mapping in mapping_report.mappings:
            field = fields_by_id.get(mapping["target_field_id"])
            if field is None:
                continue
            raw_value = mapping.get("value_sample")
            value, error = self._coerce_value(
                raw_value,
                field,
                template.enum_maps.get(field.field_id, {}),
            )
            if error is not None:
                errors.append(error)
                continue
            data[field.field_id] = value
            traces.append(
                {
                    "target_field_id": field.field_id,
                    "source_field": mapping["source_field"],
                    "operation": self._operation_for(field),
                    "status": "ok",
                }
            )

        for target_field, default_value in template.defaults.items():
            if target_field not in data and target_field in fields_by_id:
                data[target_field] = default_value
                traces.append(
                    {
                        "target_field_id": target_field,
                        "source_field": None,
                        "operation": "default",
                        "status": "ok",
                    }
                )

        for item in mapping_report.unmapped:
            if item.get("required"):
                errors.append(
                    {
                        "field_id": item["target_field_id"],
                        "level": "error",
                        "code": "required_field_unmapped",
                        "message": "Required field was not mapped.",
                    }
                )

        return TransformResult(
            data=data,
            report={
                "task_id": task_id,
                "doc_id": uir.doc_id,
                "schema_id": schema.schema_id,
                "template_id": template.template_id,
                "summary": {
                    "transformed_fields": len(data),
                    "trace_count": len(traces),
                    "error_count": len(errors),
                },
                "traces": traces,
                "errors": errors,
                "warnings": [],
            },
        )

    def _coerce_value(
        self,
        value: Any,
        field: TargetField,
        enum_map: dict[str, str],
    ) -> tuple[Any, dict[str, Any] | None]:
        if value is None:
            return None, None
        if field.type == "enum":
            if isinstance(value, str) and value in enum_map:
                return enum_map[value], None
            allowed = field.constraints.get("enum", [])
            if isinstance(value, str) and value in allowed:
                return value, None
            return value, None
        if field.type == "date":
            return self._normalize_date(value, field)
        if field.type == "datetime":
            return self._normalize_datetime(value, field)
        if field.type == "number":
            return self._normalize_number(value, field)
        if field.type.startswith("array"):
            if isinstance(value, list):
                return value, None
            return [value], None
        return value, None

    @staticmethod
    def _normalize_date(value: Any, field: TargetField) -> tuple[Any, dict[str, Any] | None]:
        if not isinstance(value, str):
            return value, {
                "field_id": field.field_id,
                "level": "error",
                "code": "date_type_error",
                "message": "Date field value is not a string.",
            }
        stripped = value.strip()
        match = re.fullmatch(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?", stripped)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}", None
        return value, {
            "field_id": field.field_id,
            "level": "error",
            "code": "date_format_error",
            "message": "Date field value does not match a supported date format.",
        }

    @staticmethod
    def _normalize_number(value: Any, field: TargetField) -> tuple[Any, dict[str, Any] | None]:
        if isinstance(value, int | float):
            return value, None
        if isinstance(value, str):
            normalized = re.sub(r"[,\s￥¥元]", "", value)
            try:
                return float(normalized), None
            except ValueError:
                return value, {
                    "field_id": field.field_id,
                    "level": "warning",
                    "code": "number_format_unparsed",
                    "message": "Number field value could not be normalized.",
                }
        return value, {
            "field_id": field.field_id,
            "level": "error",
            "code": "number_type_error",
            "message": "Number field value is not numeric.",
        }

    @staticmethod
    def _normalize_datetime(
        value: Any,
        field: TargetField,
    ) -> tuple[Any, dict[str, Any] | None]:
        if isinstance(value, str):
            stripped = value.strip()
            match = re.fullmatch(
                r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?"
                r"[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?",
                stripped,
            )
            if match:
                year, month, day, hour, minute, second = match.groups()
                try:
                    normalized = datetime(
                        int(year),
                        int(month),
                        int(day),
                        int(hour),
                        int(minute),
                        int(second or 0),
                    )
                except ValueError:
                    pass
                else:
                    return normalized.isoformat(timespec="seconds"), None
        return value, {
            "field_id": field.field_id,
            "level": "error",
            "code": "datetime_format_error",
            "message": "Datetime field value does not match a supported datetime format.",
        }

    @staticmethod
    def _operation_for(field: TargetField) -> str:
        if field.type == "date":
            return "date_normalize"
        if field.type == "datetime":
            return "datetime_normalize"
        if field.type == "number":
            return "number_normalize"
        if field.type == "enum":
            return "enum_map"
        return "rename"
