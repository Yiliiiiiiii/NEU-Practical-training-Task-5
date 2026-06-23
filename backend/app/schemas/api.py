from typing import Any

from pydantic import Field

from app.schemas.canonical import CanonicalModel
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
    options: dict[str, Any] = Field(default_factory=dict)


class TaskCreateResponse(StrictBaseModel):
    task_id: str
    status: str


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


class TaskReplayRequest(StrictBaseModel):
    reuse_confirmed_mappings: bool = True
    repeat_model_calls: bool = False
    options_override: dict[str, Any] = Field(default_factory=dict)


class TaskReplayResponse(StrictBaseModel):
    parent_task_id: str
    child_task_id: str
    status: str
    copied_candidates: int
    copied_mappings: int
    repeat_model_calls: bool


class SchemaCreateRequest(StrictBaseModel):
    target_schema: TargetSchema = Field(alias="schema")


class SchemaCreateResponse(StrictBaseModel):
    schema_id: str
    status: str


class SchemaListItem(StrictBaseModel):
    schema_id: str
    name: str
    version: str
    fields_count: int


class SchemaListResponse(StrictBaseModel):
    items: list[SchemaListItem]


class TemplateCreateRequest(StrictBaseModel):
    template: MappingTemplate


class TemplateSaveResponse(StrictBaseModel):
    template_id: str
    status: str


class TemplateListItem(StrictBaseModel):
    template_id: str
    schema_id: str
    name: str
    version: str
    aliases_count: int
    rules_count: int


class TemplateListResponse(StrictBaseModel):
    items: list[TemplateListItem]


class GenerateCandidatesRequest(StrictBaseModel):
    include_metadata: bool = True
    include_blocks: bool = True
    include_tables: bool = True


class GenerateCandidatesResponse(StrictBaseModel):
    task_id: str
    candidate_count: int
    status: str


class CandidateListItem(StrictBaseModel):
    candidate_id: str
    task_id: str
    doc_id: str
    source_path: str
    source_name: str
    display_name: str | None = None
    value_sample: Any | None = None
    inferred_type: str
    source_blocks: list[str]
    confidence: float
    evidence: list[str]


class CandidateListResponse(StrictBaseModel):
    items: list[CandidateListItem]


class MappingRunRequest(StrictBaseModel):
    enable_llm_fallback: bool = False
    review_threshold: float = 0.8


class MappingRunResponse(StrictBaseModel):
    task_id: str
    mapped_count: int
    review_required_count: int
    status: str


class MappingListItem(StrictBaseModel):
    mapping_id: str
    task_id: str
    candidate_id: str
    source_name: str
    source_path: str
    target_field_id: str
    target_field_name: str
    method: str
    confidence: float
    status: str
    need_review: bool
    evidence: list[str]


class MappingListResponse(StrictBaseModel):
    items: list[MappingListItem]


class MappingReviewItem(StrictBaseModel):
    mapping_id: str
    new_target_field_id: str | None = None
    decision: str = "confirmed"
    comment: str | None = None
    reviewer: str = "human"


class MappingReviewRequest(StrictBaseModel):
    reviews: list[MappingReviewItem]


class MappingReviewResponse(StrictBaseModel):
    task_id: str
    updated: int
    status: str


class ConvertRequest(StrictBaseModel):
    render_outputs: bool = True
    chunk_size: int = Field(default=500, gt=0)


class ConvertResponse(StrictBaseModel):
    task_id: str
    status: str
    outputs: list[str]


class CanonicalResponse(CanonicalModel):
    pass


class PackageRequest(StrictBaseModel):
    package_version: str = "1.0.0"


class PackageResponse(StrictBaseModel):
    package_id: str
    status: str
    zip_path: str
    sha256: str | None = None


class ValidationReportResponse(StrictBaseModel):
    task_id: str
    schema_id: str
    passed: bool
    summary: dict[str, Any]
    issues: list[dict[str, Any]]


class ConsistencyReportResponse(StrictBaseModel):
    task_id: str
    passed: bool
    checks: list[dict[str, Any]]
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class PackageVerifierReportResponse(StrictBaseModel):
    passed: bool
    zip_path: str
    zip_sha256: str | None = None
    summary: dict[str, Any]
    issues: list[dict[str, Any]]


class TraceListResponse(StrictBaseModel):
    task_id: str
    events: list[dict[str, Any]]
