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
