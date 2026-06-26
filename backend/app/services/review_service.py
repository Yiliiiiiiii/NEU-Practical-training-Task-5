from datetime import UTC, datetime
from typing import Any

from app.schemas.reports import MappingReport
from app.schemas.review import ReviewRecord


class ReviewService:
    def approve_review_items(
        self,
        mapping_report: MappingReport,
        reviewer: str,
        expected_pairs: set[tuple[str, str]] | None = None,
    ) -> list[ReviewRecord]:
        records: list[ReviewRecord] = []
        for item in mapping_report.review_required_items:
            source_name = self._source_name(item)
            target_field_id = item.get("target_field_id")
            if not isinstance(source_name, str) or not isinstance(target_field_id, str):
                continue
            if expected_pairs is not None and (source_name, target_field_id) not in expected_pairs:
                continue
            mapping_id = str(item.get("mapping_id", ""))
            records.append(
                ReviewRecord(
                    review_id=f"review_{mapping_report.task_id}_{mapping_id}",
                    task_id=mapping_report.task_id,
                    mapping_id=mapping_id,
                    candidate_id=str(item.get("candidate_id", "")),
                    old_target_field_id=None,
                    new_target_field_id=target_field_id,
                    reviewer=reviewer,
                    decision="approved",
                    comment="approved review-required mapping",
                    created_at=datetime.now(UTC).isoformat(),
                )
            )
        return records

    @staticmethod
    def _source_name(item: dict[str, Any]) -> str | None:
        source_field = item.get("source_field")
        if not isinstance(source_field, dict):
            return None
        source_name = source_field.get("source_name")
        return source_name if isinstance(source_name, str) else None
