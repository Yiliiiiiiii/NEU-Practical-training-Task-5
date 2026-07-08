from app.schemas.common import StrictBaseModel


class LLMCandidate(StrictBaseModel):
    doc_id: str
    target_field: str
    candidate_value: str
    source_block_ids: list[str]
    evidence_quote: str
    reason: str
    confidence: str
    risk_flags: list[str] = []
    needs_review: bool = True
    provider: str = "deepseek"
    model: str | None = None
    auto_accept_allowed: bool = False
