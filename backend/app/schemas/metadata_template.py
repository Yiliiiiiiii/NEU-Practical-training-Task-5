from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.common import StrictBaseModel

MetadataFieldType = Literal[
    "any",
    "string",
    "integer",
    "number",
    "boolean",
    "array",
    "object",
    "date",
    "datetime",
]

_SAFE_PATH = re.compile(
    r"^(?:uir\.metadata|transformed_fields|system)\.[A-Za-z][A-Za-z0-9_-]*"
    r"(?:\.[A-Za-z][A-Za-z0-9_-]*)*$"
)
_SYSTEM_VALUES = {
    "doc_id",
    "schema_id",
    "schema_version",
    "template_id",
    "template_version",
    "metadata_template_id",
    "metadata_template_version",
}


class MetadataValueSource(StrictBaseModel):
    kind: Literal["uir_metadata", "transformed_field", "default", "system", "missing"]
    path: str | None = None


class MetadataFieldConfig(StrictBaseModel):
    field_id: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    type: MetadataFieldType = "any"
    required: bool = False
    source_path: str | None = None
    default: Any = None
    allow_empty: bool = True
    description: str | None = None

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _SAFE_PATH.fullmatch(value):
            raise ValueError("source_path must use a safe whitelisted root and field syntax")
        if value.startswith("system.") and value.removeprefix("system.") not in _SYSTEM_VALUES:
            raise ValueError("source_path uses an unknown system value")
        return value


class MetadataTemplateConfig(StrictBaseModel):
    template_id: str = Field(min_length=1)
    schema_id: str = Field(min_length=1)
    version: str = "1.0.0"
    metadata_fields: list[MetadataFieldConfig] = Field(default_factory=list)

    @field_validator("metadata_fields")
    @classmethod
    def validate_unique_fields(
        cls, value: list[MetadataFieldConfig]
    ) -> list[MetadataFieldConfig]:
        field_ids = [field.field_id for field in value]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError("metadata field_id must be unique")
        return value


class MetadataFieldTrace(StrictBaseModel):
    field_id: str
    path: str
    source: MetadataValueSource
    resolved: bool
    default_used: bool = False
    value_type: str | None = None


class MetadataTemplateIssue(StrictBaseModel):
    stage: Literal["metadata_template"] = "metadata_template"
    path: str
    error_code: Literal[
        "metadata_required_missing",
        "metadata_type_mismatch",
        "metadata_empty_not_allowed",
        "metadata_source_invalid",
    ]
    message: str
    field_id: str
    expected_type: MetadataFieldType | None = None
    actual_type: str | None = None


class MetadataTemplateReport(StrictBaseModel):
    template_id: str
    schema_id: str
    version: str
    passed: bool
    field_traces: list[MetadataFieldTrace] = Field(default_factory=list)
    defaults_used: list[str] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    issues: list[MetadataTemplateIssue] = Field(default_factory=list)


class MetadataRenderResult(StrictBaseModel):
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    report: MetadataTemplateReport

    @property
    def passed(self) -> bool:
        return self.report.passed
