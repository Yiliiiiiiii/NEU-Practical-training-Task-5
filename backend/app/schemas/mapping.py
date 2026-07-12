from typing import Any, Self

from pydantic import Field, field_validator, model_validator

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
    target_hints: list[str] = Field(default_factory=list)
    evidence_type: str | None = None
    confidence_hint: float | None = None
    quality_flags: list[str] = Field(default_factory=list)


class SourceField(StrictBaseModel):
    source_path: str
    source_name: str


class MappingEvidence(StrictBaseModel):
    type: str
    message: str
    weight: float | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FieldMapping(StrictBaseModel):
    mapping_id: str
    task_id: str
    candidate_id: str
    source_field: SourceField
    source_path: str | None = None
    source_field_name: str | None = None
    target_field_id: str
    target_field_name: str
    method: str
    strategy: str | None = None
    confidence: float
    confidence_tier: str | None = None
    status: str
    operation: str = "one_to_one"
    need_review: bool = False
    value_sample: Any | None = None
    source_blocks: list[str] = Field(default_factory=list)
    evidence: list[MappingEvidence] = Field(default_factory=list)
    evidence_text: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    badcase_filter: dict[str, Any] = Field(default_factory=dict)
    review_required_reason: str | None = None
    llm_metadata: dict[str, Any] | None = None
    ranking_trace: dict[str, float] = Field(default_factory=dict)
    rejected_candidates: list[dict[str, Any]] = Field(default_factory=list)
    decision_trace: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_legacy_status(cls, value: Any) -> Any:
        if value == "confirmed":
            return "accepted"
        return value

    @field_validator("evidence", mode="before")
    @classmethod
    def normalize_legacy_evidence(cls, value: Any) -> Any:
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [
            {"type": "legacy", "message": item} if isinstance(item, str) else item for item in value
        ]

    @model_validator(mode="after")
    def populate_derived_fields(self) -> Self:
        if self.source_path is None:
            self.source_path = self.source_field.source_path
        if self.source_field_name is None:
            self.source_field_name = self.source_field.source_name
        if self.strategy is None:
            self.strategy = self.method
        if self.confidence_tier is None:
            if self.confidence >= 0.9:
                self.confidence_tier = "high"
            elif self.confidence >= 0.7:
                self.confidence_tier = "medium"
            else:
                self.confidence_tier = "low"
        if self.evidence and not self.evidence_text:
            self.evidence_text = [item.message for item in self.evidence]
        return self
