from pydantic import Field

from app.schemas.common import StrictBaseModel


class ReviewImpactItem(StrictBaseModel):
    review_id: str
    doc_id: str | None
    source_label: str
    target_field: str
    confidence_after: float


class ReviewImpactPreview(StrictBaseModel):
    review_id: str
    would_affect: list[ReviewImpactItem] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    badcase_hits: list[str] = Field(default_factory=list)


class NegativeKnowledgeRule(StrictBaseModel):
    source_label: str
    forbidden_target: str
    reason: str
    source: str = "human_rejection"
    review_id: str | None = None


class BatchReviewRequest(StrictBaseModel):
    review_ids: list[str] = Field(min_length=1, max_length=100)
    reviewer: str
    comment: str | None = None


class BatchReviewResponse(StrictBaseModel):
    processed: int
    review_ids: list[str]
    negative_rule_count: int = 0


class ReviewSummaryResponse(StrictBaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    resolution_rate: float
    negative_rule_count: int


class ReviewGroupItem(StrictBaseModel):
    key: str
    count: int
    review_ids: list[str]


class ReviewGroupedResponse(StrictBaseModel):
    group_by: str
    items: list[ReviewGroupItem]


class KnowledgeConflictItem(StrictBaseModel):
    conflict_type: str
    source_label: str
    targets: list[str]
    pack_ids: list[str] = Field(default_factory=list)
    severity: str = "high"


class KnowledgeConflictResponse(StrictBaseModel):
    total: int
    items: list[KnowledgeConflictItem]


class KnowledgePackDiffResponse(StrictBaseModel):
    pack_id: str
    added_aliases: dict[str, list[str]]
    conflicting_aliases: list[KnowledgeConflictItem] = Field(default_factory=list)


class KnowledgePackImpactResponse(StrictBaseModel):
    pack_id: str
    future_rule_count: int
    candidate_ids: list[str]
    old_snapshot_unchanged: bool = True


class KnowledgePackRollbackResponse(StrictBaseModel):
    pack_id: str
    status: str
    future_tasks_use_pack: bool
    old_snapshot_unchanged: bool
