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
    DOC_TYPE_ENUM_MAP = {
        "政策": "policy",
        "政策文件": "policy",
        "政策通知": "policy",
        "通知": "policy",
        "办法": "policy",
        "规则": "policy",
        "指南": "policy",
        "policy": "policy",
        "policy_doc": "policy",
    }
    SPLIT_ARRAY_FIELDS = {
        "application_conditions",
        "attendees",
        "applicable_scope",
        "departments",
        "participants",
        "responsible_departments",
        "responsible_units",
        "policy_measures",
        "application_materials",
        "process_steps",
        "topics",
        "decisions",
    }
    ORGANIZATION_FIELDS = {
        "applicant",
        "issuer",
        "issuing_body",
        "service_object",
    }
    CHINESE_DIGITS = {
        "零": 0,
        "〇": 0,
        "○": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }

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
                if error.get("level") != "warning":
                    continue
            data[field.field_id] = value
            trace = {
                "target_field_id": field.field_id,
                "source_field": mapping["source_field"],
                "operation": self._operation_for(field),
                "status": "ok",
            }
            if value != raw_value:
                trace.update(
                    {
                        "source_value": raw_value,
                        "normalized_value": value,
                        "normalizer": self._normalizer_for(field),
                    }
                )
            if (
                isinstance(raw_value, str)
                and field.type == "array[string]"
                and field.field_id in self.SPLIT_ARRAY_FIELDS
            ):
                trace["quality_flags"] = self._list_quality_flags(raw_value, value)
            traces.append(trace)

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
            if field.field_id == "doc_type" and isinstance(value, str):
                normalized = self.DOC_TYPE_ENUM_MAP.get(value.strip())
                if normalized is not None:
                    return normalized, None
                return value, {
                    "code": "enum_normalization_warning",
                    "failure_type": "enum_invalid",
                    "level": "warning",
                    "field_id": field.field_id,
                    "source_value": value,
                    "message": f"Unrecognized doc_type enum value: {value}",
                }
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
            if (
                isinstance(value, str)
                and field.type == "array[string]"
                and field.field_id in self.SPLIT_ARRAY_FIELDS
            ):
                return self._split_array_string(value), None
            return [value], None
        if field.field_id == "contact" and isinstance(value, str):
            return self._normalize_contact(value), None
        if field.field_id in self.ORGANIZATION_FIELDS and isinstance(value, str):
            return self._clean_organization(value), None
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
        chinese_match = re.fullmatch(
            r"(?P<year>[二〇○零一二三四五六七八九]{4})年"
            r"(?P<month>[一二三四五六七八九十]{1,3})月"
            r"(?P<day>[一二三四五六七八九十]{1,3})日"
            r"(?:上午|下午|中午|晚上|凌晨)?",
            stripped,
        )
        if chinese_match:
            year = "".join(
                str(TransformService.CHINESE_DIGITS[character])
                for character in chinese_match.group("year")
            )
            month = TransformService._chinese_cardinal(
                chinese_match.group("month")
            )
            day = TransformService._chinese_cardinal(chinese_match.group("day"))
            if month is not None and day is not None:
                return TransformService._format_date(
                    value,
                    field,
                    year,
                    str(month),
                    str(day),
                )
        match = re.fullmatch(
            r"(\d{4})\s*(?:[-/.]|年)\s*(\d{1,2})\s*(?:[-/.]|月)\s*"
            r"(\d{1,2})\s*(?:日)?(?:上午|下午|中午|晚上|凌晨)?",
            stripped,
        )
        if match:
            year, month, day = match.groups()
            return TransformService._format_date(value, field, year, month, day)
        match = re.fullmatch(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})(?:日)?", stripped)
        if match:
            year, month, day = match.groups()
            return TransformService._format_date(value, field, year, month, day)
        return value, {
            "field_id": field.field_id,
            "level": "error",
            "code": "date_format_error",
            "message": "Date field value does not match a supported date format.",
        }

    @staticmethod
    def _format_date(
        original: Any,
        field: TargetField,
        year: str,
        month: str,
        day: str,
    ) -> tuple[Any, dict[str, Any] | None]:
        try:
            normalized = datetime(int(year), int(month), int(day))
        except ValueError:
            return original, {
                "field_id": field.field_id,
                "level": "error",
                "code": "date_format_error",
                "message": "Date field value does not match a supported date format.",
            }
        return normalized.strftime("%Y-%m-%d"), None

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

    @classmethod
    def _split_array_string(cls, value: str) -> list[str]:
        cleaned = re.sub(
            r"(?m)^\s*(?:\d+|[一二三四五六七八九十]+)\s*[.．、)、]\s*",
            "",
            value.replace("\r", ""),
        )
        cleaned = re.sub(
            r"^\s*(?:申请条件|受理条件|办理条件|申报条件|申请材料|"
            r"会议议题|参会人员|适用范围)\s*[:：]\s*",
            "",
            cleaned,
        )
        items = [
            item.strip().rstrip("。")
            for item in re.split(r"[、,，;；\n]+", cleaned)
            if item.strip()
        ]
        return [item for item in items if not cls._is_list_noise(item)]

    @staticmethod
    def _is_list_noise(value: str) -> bool:
        return bool(
            re.fullmatch(r"第\s*\d+\s*页(?:\s*/\s*共\s*\d+\s*页)?", value)
            or re.match(r"^(?:责任编辑|编辑|来源)\s*[:：]", value)
        )

    @staticmethod
    def _list_quality_flags(
        source_value: str,
        normalized_value: Any,
    ) -> list[str]:
        if (
            isinstance(normalized_value, list)
            and len(normalized_value) == 1
            and "和" in source_value
            and not re.search(r"[、,，;；\n]|\d+\s*[.．、)]", source_value)
        ):
            return ["list_split_review_required"]
        return []

    @classmethod
    def _clean_organization(cls, value: str) -> str:
        cleaned = re.sub(
            r"^\s*(?:发布机构|发文机关|来源)\s*[:：]\s*",
            "",
            value,
        ).strip()
        return re.sub(
            r"(?:网站|栏目|责任编辑)\s*(?:[:：].*)?$",
            "",
            cleaned,
        ).strip()

    @classmethod
    def _chinese_cardinal(cls, value: str) -> int | None:
        if "十" not in value:
            if len(value) == 1 and value in cls.CHINESE_DIGITS:
                return cls.CHINESE_DIGITS[value]
            return None
        left, _, right = value.partition("十")
        tens = cls.CHINESE_DIGITS.get(left, 1) if left else 1
        ones = cls.CHINESE_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones

    @classmethod
    def _normalizer_for(cls, field: TargetField) -> str:
        if field.type == "date":
            return "zh_date_normalizer_v2"
        if field.type == "array[string]" and field.field_id in cls.SPLIT_ARRAY_FIELDS:
            return "list_field_normalizer_v2"
        if field.field_id in cls.ORGANIZATION_FIELDS:
            return "organization_field_cleaner_v1"
        return cls._operation_for(field)

    @staticmethod
    def _normalize_contact(value: str) -> str:
        return re.sub(r"\s*-\s*", "-", value.strip())
