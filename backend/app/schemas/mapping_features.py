from pydantic import Field

from app.schemas.common import StrictBaseModel


class MappingPairFeatures(StrictBaseModel):
    source_candidate_id: str
    source_path: str
    source_name: str
    target_field_id: str
    target_name: str
    lexical_score: float
    alias_score: float
    type_score: float
    value_score: float
    path_score: float
    context_score: float
    evidence_score: float
    negative_score: float
    source_quality_score: float
    final_score: float
    reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
