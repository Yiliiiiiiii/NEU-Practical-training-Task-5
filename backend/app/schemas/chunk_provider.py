from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import StrictBaseModel


class ChunkProviderOptions(StrictBaseModel):
    provider: Literal["internal", "topic11"] = "internal"
    fallback_to_internal: bool = True
    strict_provider: bool = False


class ChunkProviderBlock(StrictBaseModel):
    block_id: str
    type: str
    text: str
    source_blocks: list[str] = Field(default_factory=list)
    protected: bool = False
    level: int | None = None
    source_anchor: dict[str, Any] | None = None


class ChunkProviderRequest(StrictBaseModel):
    contract_version: Literal["1.0"] = "1.0"
    task_id: str
    doc_id: str
    schema_id: str
    blocks: list[ChunkProviderBlock] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_config: dict[str, Any] = Field(default_factory=dict)


class ChunkProviderChunk(StrictBaseModel):
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_block_ids: list[str] = Field(min_length=1)
    entity_ids: list[str] = Field(default_factory=list)
    parent_chunk_id: str | None = None
    title_path: list[str] = Field(default_factory=list)
    strategy: str | None = None
    chunk_index: int | None = None
    granularity: str | None = None
    quality_flags: list[str] = Field(default_factory=list)
    organization_trace: dict[str, Any] = Field(default_factory=dict)


class ChunkProviderResponse(StrictBaseModel):
    contract_version: Literal["1.0"] = "1.0"
    provider: Literal["topic11", "internal"]
    provider_version: str
    chunks: list[ChunkProviderChunk] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_chunk_ids(self) -> ChunkProviderResponse:
        chunk_ids = [chunk.chunk_id for chunk in self.chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id must be unique")
        return self


class ChunkProviderTrace(StrictBaseModel):
    requested_provider: Literal["internal", "topic11"]
    used_provider: Literal["internal", "topic11"]
    provider_version: str | None = None
    external_requested: bool = False
    external_used: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    validation_passed: bool = True
