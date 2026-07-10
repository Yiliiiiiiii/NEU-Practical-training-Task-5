from __future__ import annotations

from typing import Any, Literal

from app.schemas.common import StrictBaseModel


class ConversionAssertionIssue(StrictBaseModel):
    assertion_id: str
    severity: Literal["error", "warning"]
    path: str
    operator: str
    message: str
    expected: Any | None = None
    actual_preview: Any | None = None
    source_path: str | None = None
    source_candidate_id: str | None = None
    mapping_method: str | None = None


class ConversionAssertionResult(StrictBaseModel):
    assertion_id: str
    status: Literal["passed", "failed", "skipped"]
    severity: Literal["error", "warning"]
    path: str
    operator: str


class ConversionAssertionReport(StrictBaseModel):
    contract_version: str = "1.0"
    task_id: str
    schema_pack_id: str
    schema_pack_version: str
    schema_id: str
    assertion_set_version: str
    passed: bool
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_count: int
    warning_count: int
    results: list[ConversionAssertionResult]
    issues: list[ConversionAssertionIssue]
    generated_at: str
