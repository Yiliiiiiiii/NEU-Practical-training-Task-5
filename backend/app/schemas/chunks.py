from pydantic import Field

from app.schemas.common import StrictBaseModel


class ChunkLabels(StrictBaseModel):
    content_tags: list[str] = Field(default_factory=list)
    management_tags: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)


class Chunk(StrictBaseModel):
    chunk_id: str
    order: int
    text: str
    source_blocks: list[str] = Field(default_factory=list)
    title_path: list[str] = Field(default_factory=list)
    labels: ChunkLabels = Field(default_factory=ChunkLabels)
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    text_hash: str = ""


class ChunksJSON(StrictBaseModel):
    chunks_version: str = "1.0"
    doc_id: str
    task_id: str
    chunks: list[Chunk] = Field(default_factory=list)
