from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import StrictBaseModel


class SourceLink(StrictBaseModel):
    block_id: str
    source_path: str | None = None
    page_no: int | None = None
    bbox: list[float] | None = None
    anchor_text: str | None = None


class EntityTag(StrictBaseModel):
    text: str
    entity_type: str = "unknown"
    normalized_id: str | None = None
    source: Literal["schema_field", "metadata", "rule", "placeholder"] = "placeholder"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ChunkTags(StrictBaseModel):
    content: list[str] = Field(default_factory=list)
    management: list[str] = Field(default_factory=list)
    quality: list[str] = Field(default_factory=list)


class ContentOrganizationOptions(StrictBaseModel):
    chunk_strategy: Literal[
        "fixed_window",
        "heading_aware",
        "source_block_aware",
        "table_protect",
        "parent_child",
    ] = "heading_aware"
    target_tokens: int = Field(default=768, gt=0)
    min_tokens: int = Field(default=128, gt=0)
    max_tokens: int = Field(default=1024, gt=0)
    overlap_tokens: int = Field(default=80, ge=0)
    protect_tables: bool = True
    protect_lists: bool = True
    protect_code_blocks: bool = True
    enable_parent_child: bool = False
    enable_light_semantic_boundary: bool = True
    summary_mode: Literal["none", "deterministic"] = "deterministic"
    keyword_mode: Literal["none", "deterministic"] = "deterministic"

    @model_validator(mode="after")
    def validate_token_window(self):
        if self.max_tokens < self.min_tokens:
            raise ValueError("max_tokens must be greater than or equal to min_tokens")
        if not self.min_tokens <= self.target_tokens <= self.max_tokens:
            raise ValueError("target_tokens must be between min_tokens and max_tokens")
        if self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be less than target_tokens")
        return self


class OrganizedChunk(StrictBaseModel):
    chunk_id: str
    parent_chunk_id: str | None = None
    doc_id: str | None = None
    task_id: str | None = None
    index: int
    chunk_index: int | None = None
    strategy: str | None = None
    granularity: Literal["parent", "child"] | None = None
    text: str
    token_estimate: int
    char_count: int | None = None
    title: str | None = None
    title_path: list[str] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    source_links: list[SourceLink] = Field(default_factory=list)
    content_tags: list[str] = Field(default_factory=list)
    management_tags: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    tags: ChunkTags = Field(default_factory=ChunkTags)
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    entity_tags: list[EntityTag] = Field(default_factory=list)
    created_by: str = "ChunkOrganizerService"
    organization_trace: dict[str, Any] = Field(default_factory=dict)


class ContentOrganizationReport(StrictBaseModel):
    task_id: str
    doc_id: str
    chunk_count: int
    chunks_with_summary: int
    chunks_with_keywords: int
    chunks_with_source_links: int
    chunks_with_content_tags: int
    chunks_with_quality_tags: int
    warnings: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
