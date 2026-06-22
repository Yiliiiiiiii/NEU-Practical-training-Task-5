from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class CanonicalField(StrictBaseModel):
    value: Any
    type: str
    source_candidates: list[str] = Field(default_factory=list)
    source_blocks: list[str] = Field(default_factory=list)


class CanonicalBlock(StrictBaseModel):
    block_id: str
    type: str
    level: int | None = None
    text: str
    source_blocks: list[str]
    text_hash: str | None = None


class CanonicalAsset(StrictBaseModel):
    asset_id: str
    type: str
    path: str
    source_block_id: str | None = None


class CanonicalModel(StrictBaseModel):
    canonical_version: str
    task_id: str
    doc_id: str
    schema_id: str
    doc_meta: dict[str, Any] = Field(default_factory=dict)
    fields: dict[str, CanonicalField] = Field(default_factory=dict)
    blocks: list[CanonicalBlock] = Field(default_factory=list)
    assets: list[CanonicalAsset] = Field(default_factory=list)
