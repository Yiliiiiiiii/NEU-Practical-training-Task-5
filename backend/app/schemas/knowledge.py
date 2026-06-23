from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


CandidateType = Literal[
    "alias_candidate",
    "regex_candidate",
    "enum_map_candidate",
    "default_candidate",
    "transform_candidate",
    "gold_mapping_candidate",
    "badcase_candidate",
]
CandidateStatus = Literal["pending", "approved", "rejected", "superseded"]
CandidateDecision = Literal["approved", "rejected"]
KnowledgePackStatus = Literal["draft", "active", "superseded"]


class RealRunView(StrictBaseModel):
    real_run_id: str
    task_id: str
    doc_id: str
    schema_id: str
    template_id: str
    input_hash: str
    status: str
    summary: dict[str, Any] = Field(default_factory=dict)
    report_paths: dict[str, str] = Field(default_factory=dict)


class LearningCandidateView(StrictBaseModel):
    candidate_id: str
    real_run_id: str
    task_id: str
    candidate_type: CandidateType
    status: CandidateStatus
    risk_level: Literal["low", "medium", "high"]
    target_field_id: str | None = None
    proposed_payload: dict[str, Any] = Field(default_factory=dict)
    final_payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    generator: str
    confidence: float


class CandidateDecisionRequest(StrictBaseModel):
    decision: CandidateDecision
    reviewer: str = "human"
    final_payload: dict[str, Any] = Field(default_factory=dict)
    reason: str


class CandidateListResponse(StrictBaseModel):
    items: list[LearningCandidateView]


class KnowledgePackCreateRequest(StrictBaseModel):
    name: str
    scope: dict[str, str] = Field(default_factory=dict)
    candidate_ids: list[str]
    reviewer: str = "human"


class KnowledgePackView(StrictBaseModel):
    pack_id: str
    name: str
    scope: dict[str, str] = Field(default_factory=dict)
    status: KnowledgePackStatus
    version: str
    item_count: int
    regression_report_path: str | None = None
    reviewer: str


class KnowledgePackListResponse(StrictBaseModel):
    items: list[KnowledgePackView]


class KnowledgeMetricsResponse(StrictBaseModel):
    real_runs: int
    pending_candidates: int
    approved_candidates: int
    rejected_candidates: int
    active_packs: int
