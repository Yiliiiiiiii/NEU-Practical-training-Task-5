from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class UIRSource(StrictBaseModel):
    source_type: str
    source_name: str
    upstream_agents: list[str] = Field(default_factory=list)


class SourceAnchor(StrictBaseModel):
    page: int | None = None
    bbox: list[float] | None = None


class UIRBlock(StrictBaseModel):
    block_id: str
    type: str
    level: int | None = None
    text: str | None = None
    source_anchor: SourceAnchor | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class UIRAsset(StrictBaseModel):
    asset_id: str
    type: str
    path: str
    source_block_id: str | None = None
    sha256: str | None = None


class UIRDocument(StrictBaseModel):
    uir_version: str
    doc_id: str
    source: UIRSource | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    blocks: list[UIRBlock] = Field(default_factory=list)
    assets: list[UIRAsset] = Field(default_factory=list)
    normalization_records: list[dict[str, Any]] = Field(default_factory=list)
