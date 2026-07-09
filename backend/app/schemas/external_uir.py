import hashlib
import json
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.uir import UIRDocument


class ExternalUIRSource(StrictBaseModel):
    source_system: str
    source_format: str | None = None
    source_version: str | None = None
    source_url: str | None = None
    source_sha256: str | None = None


class ExternalUIRPayload(StrictBaseModel):
    external_doc_id: str | None = None
    source: ExternalUIRSource
    payload: dict[str, Any]
    hints: dict[str, Any] = Field(default_factory=dict)


class AdapterTraceItem(StrictBaseModel):
    external_path: str
    canonical_path: str
    target_block_id: str
    conversion_rule: str
    source_value_preview: str
    strategy: Literal["rule", "heuristic", "llm_suggestion", "fallback"]
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    review_required: bool = False
    warning: str | None = None


class ExternalUIRLLMSuggestion(StrictBaseModel):
    external_path: str
    target_uir_location: str
    operation: str
    confidence: float
    evidence: str
    review_required: bool
    reason: str


class ExternalUIRLLMSuggestionReport(StrictBaseModel):
    suggestions: list[ExternalUIRLLMSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    must_not_auto_accept_mapping: bool = True
    must_not_activate_catalog: bool = True


class AdapterReport(StrictBaseModel):
    adapter_id: str = "external_uir_legacy"
    adapter_version: str
    source_system: str
    external_doc_id: str | None
    generated_doc_id: str
    status: Literal["passed", "review_required", "failed"]
    trace_items: list[AdapterTraceItem]
    dialect: str | None = None
    detected_dialect: str | None = None
    trace_coverage: float = 0.0
    block_count: int = 0
    table_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    route_hints: list[str] = Field(default_factory=list)
    assisted_suggestions: list[ExternalUIRLLMSuggestion] = Field(default_factory=list)
    llm_used: bool = False
    llm_auto_accepted_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    raw_payload_hash: str


class RouteEvidence(StrictBaseModel):
    evidence_type: Literal[
        "keyword", "field_hint", "metadata", "table_label", "adapter_hint"
    ]
    value: str
    source_path: str | None = None
    weight: float
    matched_schema: str


class SchemaRouteCandidate(StrictBaseModel):
    schema_id: str
    template_id: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    evidence: list[RouteEvidence] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    source: str = "builtin_signals"


class SchemaRouteDecision(StrictBaseModel):
    selected_schema_id: str | None
    selected_template_id: str | None
    confidence: float
    reason: str = ""
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False
    candidates: list[SchemaRouteCandidate] = Field(default_factory=list)
    decision_reason: str = ""
    route_version: str = "2.0"


class ExternalUIRConvertRequest(StrictBaseModel):
    payload: dict[str, Any]
    source_system: str = "external"
    dialect_hint: str | None = None
    route_schema: bool = True
    allow_llm: bool = False
    llm_mode: str | None = None
    dry_run: bool = True


class ExternalUIRConvertResponse(StrictBaseModel):
    standard_uir: UIRDocument
    adapter_report: AdapterReport
    route_report: SchemaRouteDecision | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExternalUIRImportRequest(StrictBaseModel):
    payload: dict[str, Any]
    source_system: str = "external"
    dialect_hint: str | None = None
    route_schema: bool = True
    allow_llm: bool = False
    llm_mode: str | None = None


class ExternalUIRDocumentSummary(StrictBaseModel):
    doc_id: str
    title: str | None = None
    block_count: int


class ExternalUIRImportResponse(StrictBaseModel):
    doc_id: str
    document: ExternalUIRDocumentSummary
    adapter_report: AdapterReport
    route_report: SchemaRouteDecision | None = None
    warnings: list[str] = Field(default_factory=list)


class ExternalUIRCreateTaskRequest(StrictBaseModel):
    doc_id: str
    schema_id: str
    template_id: str
    schema_version: str = "1.0.0"
    template_version: str = "1.0.0"
    options: dict[str, Any] = Field(default_factory=dict)
    route_report: SchemaRouteDecision | None = None
    adapter_report: AdapterReport | None = None


class ExternalUIRCreateTaskResponse(StrictBaseModel):
    task_id: str
    status: str
    review_required: bool = False
    warnings: list[str] = Field(default_factory=list)


def hash_payload(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()
