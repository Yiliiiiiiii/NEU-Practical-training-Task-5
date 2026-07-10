from typing import Any, Self

from pydantic import Field, model_validator

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


class UIREntity(StrictBaseModel):
    mention: str = Field(min_length=1)
    canonical_name: str | None = None
    entity_type: str = "unknown"
    normalized_id: str | None = None
    link_status: str = Field(default="unlinked", pattern=r"^(linked|unlinked|nil)$")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_block_ids: list[str] = Field(default_factory=list)
    source_agent: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_linked_identity(self) -> "UIREntity":
        if self.link_status == "linked" and not self.normalized_id:
            raise ValueError("linked entity requires normalized_id")
        return self


class UIRDocument(StrictBaseModel):
    uir_version: str
    doc_id: str
    source: UIRSource | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    blocks: list[UIRBlock] = Field(default_factory=list)
    assets: list[UIRAsset] = Field(default_factory=list)
    entities: list[UIREntity] = Field(default_factory=list)
    normalization_records: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entity_source_blocks(self) -> Self:
        block_ids = {block.block_id for block in self.blocks}
        for entity in self.entities:
            unknown = sorted(set(entity.source_block_ids) - block_ids)
            if unknown:
                raise ValueError(
                    f"entity source_block_ids contains unknown block_id {unknown[0]}"
                )
        return self
