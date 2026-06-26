from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class FieldCandidate(StrictBaseModel):
    candidate_id: str
    task_id: str
    doc_id: str
    source_path: str
    source_name: str
    display_name: str | None = None
    value_sample: Any | None = None
    inferred_type: str
    source_blocks: list[str] = Field(default_factory=list)
    confidence: float
    evidence: list[str] = Field(default_factory=list)


class SourceField(StrictBaseModel):
    source_path: str
    source_name: str


class FieldMapping(StrictBaseModel):
    mapping_id: str
    task_id: str
    candidate_id: str
    source_field: SourceField
    target_field_id: str
    target_field_name: str
    method: str
    confidence: float
    status: str
    need_review: bool = False
    value_sample: Any | None = None
    source_blocks: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
