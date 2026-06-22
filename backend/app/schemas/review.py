from app.schemas.common import StrictBaseModel


class ReviewRecord(StrictBaseModel):
    review_id: str
    task_id: str
    mapping_id: str
    candidate_id: str
    old_target_field_id: str | None = None
    new_target_field_id: str | None = None
    reviewer: str
    decision: str
    comment: str | None = None
    created_at: str
