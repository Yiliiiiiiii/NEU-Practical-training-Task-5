from sqlalchemy.orm import Session

from app.db.models import ConversionTask, FieldMappingRecord, ReviewRecord
from app.schemas.api import MappingReviewItem
from app.utils.ids import new_id


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_mapping_reviews(self, task_id: str, reviews: list[MappingReviewItem]) -> int:
        task = self._get_task(task_id)
        updated = 0
        for review in reviews:
            mapping = self._get_mapping(task_id, review.mapping_id)
            old_target = mapping.target_field_id
            if review.new_target_field_id:
                mapping.target_field_id = review.new_target_field_id
            mapping.status = self._mapping_status(review.decision)
            mapping.need_review = False
            self.db.add(
                ReviewRecord(
                    review_id=new_id("rev"),
                    task_id=task_id,
                    mapping_id=mapping.mapping_id,
                    old_target_field_id=old_target,
                    new_target_field_id=mapping.target_field_id,
                    decision=review.decision,
                    comment=review.comment,
                    reviewer=review.reviewer,
                )
            )
            updated += 1

        remaining_reviews = (
            self.db.query(FieldMappingRecord)
            .filter(
                FieldMappingRecord.task_id == task_id,
                FieldMappingRecord.need_review.is_(True),
            )
            .count()
        )
        task.status = "review_required" if remaining_reviews else "mapping_completed"
        self.db.commit()
        return updated

    def _get_task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _get_mapping(self, task_id: str, mapping_id: str) -> FieldMappingRecord:
        mapping = self.db.get(FieldMappingRecord, mapping_id)
        if mapping is None or mapping.task_id != task_id:
            raise LookupError("mapping not found")
        return mapping

    @staticmethod
    def _mapping_status(decision: str) -> str:
        if decision in {"confirmed", "changed"}:
            return "confirmed"
        if decision == "rejected":
            return "rejected"
        return "reviewed"
