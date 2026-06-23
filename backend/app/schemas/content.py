from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class ContentSchemaRef(StrictBaseModel):
    schema_id: str
    version: str


class ContentMetadata(StrictBaseModel):
    source_name: str | None = None
    document_summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    content_tags: list[str] = Field(default_factory=list)
    management_tags: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    upstream_entities: list[str] = Field(default_factory=list)


class ContentBlock(StrictBaseModel):
    block_id: str
    type: str
    level: int | None = None
    text: str
    source_blocks: list[str] = Field(default_factory=list)
    text_hash: str | None = None


class ContentAsset(StrictBaseModel):
    asset_id: str
    type: str
    path: str
    source_block_id: str | None = None


class ContentJSON(StrictBaseModel):
    content_version: str = "1.1"
    doc_id: str
    task_id: str
    schema_ref: ContentSchemaRef
    metadata: ContentMetadata = Field(default_factory=ContentMetadata)
    data: dict[str, Any] = Field(default_factory=dict)
    blocks: list[ContentBlock] = Field(default_factory=list)
    assets: list[ContentAsset] = Field(default_factory=list)
