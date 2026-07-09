from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument


class MetadataTemplateConfig(StrictBaseModel):
    template_id: str
    schema_id: str
    version: str = "1.0.0"
    metadata_fields: list[dict[str, Any]] = Field(default_factory=list)


class ContentOrganizationConfig(StrictBaseModel):
    chunk_strategy: str = "source_block_aware"
    target_tokens: int = 1200
    min_tokens: int = 1
    max_tokens: int = 1400
    overlap_tokens: int = 0
    protect_tables: bool = True
    protect_lists: bool = True
    protect_code_blocks: bool = True
    enable_parent_child: bool = False
    summary_mode: str = "deterministic"
    keyword_mode: str = "deterministic"


class Topic5ConvertRequest(StrictBaseModel):
    uir: UIRDocument
    target_schema: TargetSchema
    mapping_template: MappingTemplate
    metadata_template: MetadataTemplateConfig | None = None
    content_organization: ContentOrganizationConfig = Field(
        default_factory=ContentOrganizationConfig
    )
    options: dict[str, Any] = Field(default_factory=dict)


class Topic5ConvertResponse(StrictBaseModel):
    task_id: str
    status: str
    schema_id: str
    template_id: str
    content_json: dict[str, Any]
    content_markdown: str
    chunks: list[dict[str, Any]]
    mapping_report: dict[str, Any]
    transform_report: dict[str, Any]
    validation_report: dict[str, Any]
    content_organization_report: dict[str, Any]
    manifest: dict[str, Any] | None = None
    package_zip_path: str | None = None
    package_metadata: dict[str, Any] | None = None
    verifier_report: dict[str, Any] | None = None
