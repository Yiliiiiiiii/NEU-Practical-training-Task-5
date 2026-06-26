from typing import Any, Literal

from pydantic import Field

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


class OrganizedChunk(StrictBaseModel):
    chunk_id: str
    doc_id: str | None = None
    task_id: str | None = None
    index: int
    text: str
    token_estimate: int
    title_path: list[str] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    source_links: list[SourceLink] = Field(default_factory=list)
    tags: ChunkTags = Field(default_factory=ChunkTags)
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    entity_tags: list[EntityTag] = Field(default_factory=list)
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
