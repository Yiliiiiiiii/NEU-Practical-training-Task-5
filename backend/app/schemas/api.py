from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument


class ErrorDetail(StrictBaseModel):
    path: str | None = None
    message: str


class ErrorBody(StrictBaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(StrictBaseModel):
    error: ErrorBody


class DocumentImportRequest(StrictBaseModel):
    uir: UIRDocument


class DocumentImportResponse(StrictBaseModel):
    doc_id: str
    status: str
    block_count: int


class DocumentListItem(StrictBaseModel):
    doc_id: str
    title: str | None = None
    block_count: int


class DocumentListResponse(StrictBaseModel):
    items: list[DocumentListItem]
    total: int


class DocumentDetailResponse(StrictBaseModel):
    doc_id: str
    metadata: dict[str, Any]
    blocks_preview: list[dict[str, Any]]


class TaskCreateRequest(StrictBaseModel):
    doc_id: str
    schema_id: str
    template_id: str
    schema_version: str = "1.0.0"
    template_version: str = "1.0.0"
    schema_pack_id: str | None = None
    enable_legacy_transform_heuristics: bool = False
    options: dict[str, Any] = Field(default_factory=dict)


class TaskCreateResponse(StrictBaseModel):
    task_id: str
    status: str


class TaskExecuteResponse(StrictBaseModel):
    task_id: str
    status: str
    report_paths: dict[str, str] = Field(default_factory=dict)
    package_zip_path: str | None = None
    review_required_count: int = 0
    unmapped_required_count: int = 0


class TaskListItem(StrictBaseModel):
    task_id: str
    doc_id: str
    schema_id: str
    template_id: str
    status: str


class TaskListResponse(StrictBaseModel):
    items: list[TaskListItem]
    total: int


class TaskDetailResponse(StrictBaseModel):
    task_id: str
    status: str
    doc_id: str
    schema_id: str
    schema_version: str
    template_id: str
    template_version: str
    input_hash: str
    options: dict[str, Any]
    report_paths: dict[str, str] = Field(default_factory=dict)
    package_zip_path: str | None = None


class EvaluationReportResponse(StrictBaseModel):
    status: str
    report: dict[str, Any] | None = None
    recommended_command: str | None = None


class SchemaListResponse(StrictBaseModel):
    items: list[TargetSchema]
    total: int


class TemplateListResponse(StrictBaseModel):
    items: list[MappingTemplate]
    total: int


class SchemaCatalogItem(StrictBaseModel):
    schema_id: str
    name: str
    version: str
    status: str
    content_hash: str


class SchemaCatalogResponse(StrictBaseModel):
    items: list[SchemaCatalogItem]
    total: int


class SchemaCreateRequest(StrictBaseModel):
    target_schema: TargetSchema = Field(alias="schema")
    status: str = "draft"


class SchemaStatusResponse(StrictBaseModel):
    schema_id: str
    version: str
    status: str


class TemplateCatalogItem(StrictBaseModel):
    template_id: str
    schema_id: str
    name: str
    version: str
    status: str
    content_hash: str


class TemplateCatalogResponse(StrictBaseModel):
    items: list[TemplateCatalogItem]
    total: int


class TemplateCreateRequest(StrictBaseModel):
    template: MappingTemplate
    status: str = "draft"


class TemplateStatusResponse(StrictBaseModel):
    template_id: str
    version: str
    status: str


class ReviewRecordResponse(StrictBaseModel):
    review_id: str
    task_id: str
    doc_id: str | None = None
    schema_id: str | None = None
    template_id: str | None = None
    source_field_name: str | None = None
    source_path: str | None = None
    target_field_id: str | None = None
    suggested_by: str | None = None
    confidence: float | None = None
    reason: str | None = None
    status: str
    reviewer: str
    review_comment: str | None = None
    created_at: str
    updated_at: str


class ReviewListResponse(StrictBaseModel):
    items: list[ReviewRecordResponse]
    total: int


class ReviewDecisionRequest(StrictBaseModel):
    reviewer: str = "demo_user"
    comment: str | None = None
    create_knowledge_candidate: bool = False


class KnowledgeCandidateResponse(StrictBaseModel):
    candidate_id: str
    review_id: str
    schema_id: str
    template_id: str
    target_field_id: str
    alias: str
    candidate_type: str
    support_count: int
    badcase_hit: bool
    status: str
    created_at: str
    updated_at: str


class KnowledgeCandidateListResponse(StrictBaseModel):
    items: list[KnowledgeCandidateResponse]
    total: int


class KnowledgePackResponse(StrictBaseModel):
    pack_id: str
    name: str
    schema_id: str
    template_id: str
    version: str
    status: str
    created_by: str
    metadata: dict[str, Any]
    items: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    activated_at: str | None = None
    updated_at: str


class KnowledgePackListResponse(StrictBaseModel):
    items: list[KnowledgePackResponse]
    total: int


class KnowledgePackCreateRequest(StrictBaseModel):
    schema_id: str
    template_id: str
    name: str | None = None
    created_by: str = "demo_user"


class KnowledgeMetricsResponse(StrictBaseModel):
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int
    pending_candidates: int
    accepted_candidates: int
    rejected_candidates: int
    blocked_candidates: int
    draft_packs: int
    active_packs: int
    archived_packs: int


class AuditLogResponse(StrictBaseModel):
    audit_id: str
    created_at: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    actor_type: str
    actor_id: str | None = None
    api_key_hash_prefix: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    success: bool
    error_code: str | None = None
    metadata: dict[str, Any]


class AuditLogListResponse(StrictBaseModel):
    items: list[AuditLogResponse]
    total: int
