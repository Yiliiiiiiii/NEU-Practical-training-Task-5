from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class ReportIssue(StrictBaseModel):
    level: str
    message: str
    stage: str | None = None
    field_id: str | None = None
    path: str | None = None
    code: str | None = None
    failure_type: str | None = None
    source_value: Any | None = None
    suggested_normalized_value: Any | None = None


class MappingReport(StrictBaseModel):
    task_id: str
    schema_id: str
    summary: dict[str, Any]
    mappings: list[dict[str, Any]] = Field(default_factory=list)
    unmapped: list[dict[str, Any]] = Field(default_factory=list)
    review_required_items: list[dict[str, Any]] = Field(default_factory=list)


class ValidationReport(StrictBaseModel):
    task_id: str
    schema_id: str
    passed: bool
    schema_valid: bool | None = None
    strict_semantic_valid: bool | None = None
    summary: dict[str, Any]
    issues: list[ReportIssue] = Field(default_factory=list)


class ConsistencyCheck(StrictBaseModel):
    check_name: str
    passed: bool
    severity: str = "critical"
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ConsistencyReport(StrictBaseModel):
    task_id: str
    passed: bool
    checks: list[ConsistencyCheck] = Field(default_factory=list)
    errors: list[ReportIssue] = Field(default_factory=list)
    warnings: list[ReportIssue] = Field(default_factory=list)
    manifest_sha256: str | None = None


class ConversionTrace(StrictBaseModel):
    trace_id: str
    task_id: str
    doc_id: str | None = None
    stage: str
    action: str
    target_field_id: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    rule_id: str | None = None
    reason: str
    status: str
    created_at: str
