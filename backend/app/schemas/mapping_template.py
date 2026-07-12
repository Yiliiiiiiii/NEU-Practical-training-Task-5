from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.schemas.common import StrictBaseModel
from app.schemas.transform import TransformRule


class RegexRule(StrictBaseModel):
    target_field_id: str
    pattern: str
    group: int = 0


class MappingScoringPolicy(StrictBaseModel):
    lexical_weight: float = 0.25
    alias_weight: float = 0.20
    type_weight: float = 0.15
    value_shape_weight: float = 0.10
    path_weight: float = 0.10
    context_weight: float = 0.10
    source_quality_weight: float = 0.10

    @field_validator("*")
    @classmethod
    def weight_must_be_a_probability(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("scoring weights must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def weights_must_sum_to_one(self) -> Self:
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("scoring weights must sum to 1")
        return self


class SourceReuseRule(StrictBaseModel):
    source_path: str
    target_field_ids: list[str]
    reason: str


class MappingCardinalityRule(StrictBaseModel):
    operation: Literal["one_to_many", "many_to_one"]
    target_field_id: str
    source_paths: list[str]
    reason: str


class MappingConstraintPolicy(StrictBaseModel):
    min_type_score: float = 0.0
    field_min_scores: dict[str, float] = Field(default_factory=dict)
    source_reuse_rules: list[SourceReuseRule] = Field(default_factory=list)
    cardinality_rules: list[MappingCardinalityRule] = Field(default_factory=list)

    @field_validator("min_type_score")
    @classmethod
    def min_type_score_must_be_a_probability(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("minimum type score must be between 0 and 1")
        return value

    @field_validator("field_min_scores")
    @classmethod
    def field_scores_must_be_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not 0.0 <= score <= 1.0 for score in value.values()):
            raise ValueError("field minimum scores must be between 0 and 1")
        return value


class MappingTemplate(StrictBaseModel):
    template_id: str
    schema_id: str
    name: str
    version: str
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    regex_rules: list[RegexRule] = Field(default_factory=list)
    transform_rules: list[TransformRule] = Field(default_factory=list)
    defaults: dict[str, object] = Field(default_factory=dict)
    enum_maps: dict[str, dict[str, str]] = Field(default_factory=dict)
    scoring: MappingScoringPolicy = Field(default_factory=MappingScoringPolicy)
    evidence_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "metadata": 0.80,
            "key_value": 0.85,
            "table": 0.90,
            "block": 0.70,
            "paragraph_regex": 0.75,
            "aggregate_blocks": 0.60,
        }
    )
    unknown_evidence_policy: Literal["neutral", "reject"] = "neutral"
    neutral_evidence_weight: float = 0.70
    constraints: MappingConstraintPolicy = Field(default_factory=MappingConstraintPolicy)

    @field_validator("neutral_evidence_weight")
    @classmethod
    def neutral_weight_must_be_a_probability(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("neutral evidence weight must be between 0 and 1")
        return value

    @field_validator("evidence_weights")
    @classmethod
    def evidence_weights_must_be_probabilities(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not name.strip() for name in value):
            raise ValueError("evidence type names must not be empty")
        if any(not 0.0 <= weight <= 1.0 for weight in value.values()):
            raise ValueError("evidence weights must be between 0 and 1")
        return value
