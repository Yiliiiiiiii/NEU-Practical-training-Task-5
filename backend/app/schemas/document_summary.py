from typing import Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


class SummarySentenceTrace(StrictBaseModel):
    summary_sentence: str
    source_block_id: str
    source_text_span: str


class DocumentSummary(StrictBaseModel):
    text: str = ""
    mode: Literal["none", "deterministic", "extractive"] = "extractive"
    source_block_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    sentence_traces: list[SummarySentenceTrace] = Field(default_factory=list)
    char_count: int = Field(default=0, ge=0)
    generated_by: str = "DocumentSummaryService"
    faithfulness_passed: bool = True
    warnings: list[str] = Field(default_factory=list)
