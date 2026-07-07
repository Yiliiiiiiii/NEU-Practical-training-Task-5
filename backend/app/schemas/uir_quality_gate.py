from typing import Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel

UIRQualityGateStatus = Literal["pass", "review", "reject", "unsupported"]
UIRQualityGateSeverity = Literal["info", "warning", "error"]


class UIRQualityGateIssue(StrictBaseModel):
    code: str
    severity: UIRQualityGateSeverity
    action: UIRQualityGateStatus
    message: str
    path: str | None = None


class UIRQualityGatePolicy(StrictBaseModel):
    allow_auto_accept: bool = False
    require_review_for_high_risk_fields: bool = True
    allow_llm_suggestions: bool = False


class UIRQualityGateReport(StrictBaseModel):
    doc_id: str
    status: UIRQualityGateStatus
    quality_score: float
    supported_doc_type: str | None = None
    selected_schema_id: str | None = None
    selected_template_id: str | None = None
    schema_route_confidence: float = 0.0
    mapping_policy: UIRQualityGatePolicy = Field(default_factory=UIRQualityGatePolicy)
    issues: list[UIRQualityGateIssue] = Field(default_factory=list)
