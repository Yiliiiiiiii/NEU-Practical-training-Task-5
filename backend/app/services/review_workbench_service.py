import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.models import ConversionTask, ReviewRecord
from app.schemas.review_workbench import (
    BatchReviewResponse,
    NegativeKnowledgeRule,
    ReviewGroupedResponse,
    ReviewGroupItem,
    ReviewImpactItem,
    ReviewImpactPreview,
    ReviewSummaryResponse,
)
from app.services.review_knowledge_workflow_service import (
    ReviewKnowledgeWorkflowService,
)
from app.services.storage_service import StorageService


class ReviewWorkbenchService:
    negative_rules_path = "knowledge/negative_rules.json"

    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.workflow = ReviewKnowledgeWorkflowService(db)

    def impact_preview(self, review_id: str) -> ReviewImpactPreview:
        review = self.workflow.get_review(review_id)
        related = [
            item
            for item in self.workflow.list_reviews()
            if item.review_id != review.review_id
            and item.status == "pending"
            and item.schema_id == review.schema_id
            and item.template_id == review.template_id
            and item.source_field_name == review.source_field_name
            and item.target_field_id == review.target_field_id
        ]
        badcase_hits = [review.review_id] if self._badcase_hit(review) else []
        return ReviewImpactPreview(
            review_id=review.review_id,
            would_affect=[
                ReviewImpactItem(
                    review_id=item.review_id,
                    doc_id=item.doc_id,
                    source_label=str(item.source_field_name or ""),
                    target_field=str(item.target_field_id or ""),
                    confidence_after=round(max(float(item.confidence or 0), 0.88), 4),
                )
                for item in related
            ],
            risk_flags=self._risk_flags(review),
            badcase_hits=badcase_hits,
        )

    def record_negative_rule(
        self,
        review: ReviewRecord,
        *,
        reason: str,
    ) -> NegativeKnowledgeRule:
        if not review.source_field_name or not review.target_field_id:
            raise ValueError("review lacks source or target for negative knowledge")
        rule = NegativeKnowledgeRule(
            source_label=review.source_field_name,
            forbidden_target=review.target_field_id,
            reason=reason,
            source="human_rejection",
            review_id=review.review_id,
        )
        rules = self.list_negative_rules()
        pair = (rule.source_label, rule.forbidden_target)
        rules = [
            item
            for item in rules
            if (item.source_label, item.forbidden_target) != pair
        ]
        rules.append(rule)
        self.storage.save_json(
            self.negative_rules_path,
            [item.model_dump(mode="json") for item in rules],
        )
        return rule

    def list_negative_rules(self) -> list[NegativeKnowledgeRule]:
        try:
            payload = self.storage.read_json(self.negative_rules_path)
        except FileNotFoundError:
            return []
        if not isinstance(payload, list):
            return []
        return [NegativeKnowledgeRule.model_validate(item) for item in payload]

    def batch_approve(
        self,
        review_ids: list[str],
        *,
        reviewer: str,
        comment: str | None,
    ) -> BatchReviewResponse:
        reviews = [self.workflow.get_review(review_id) for review_id in review_ids]
        self._validate_batch(reviews)
        for review in reviews:
            self.workflow.approve_review(
                review.review_id,
                reviewer=reviewer,
                comment=comment,
                create_knowledge_candidate=True,
            )
        return BatchReviewResponse(
            processed=len(reviews),
            review_ids=review_ids,
        )

    def batch_reject(
        self,
        review_ids: list[str],
        *,
        reviewer: str,
        comment: str | None,
    ) -> BatchReviewResponse:
        reviews = [self.workflow.get_review(review_id) for review_id in review_ids]
        negative_count = 0
        for review in reviews:
            rejected = self.workflow.reject_review(
                review.review_id,
                reviewer=reviewer,
                comment=comment,
            )
            self.record_negative_rule(
                rejected,
                reason=comment or rejected.reason or "human rejection",
            )
            negative_count += 1
        return BatchReviewResponse(
            processed=len(reviews),
            review_ids=review_ids,
            negative_rule_count=negative_count,
        )

    def summary(self) -> ReviewSummaryResponse:
        reviews = self.workflow.list_reviews()
        resolved = sum(1 for item in reviews if item.status in {"approved", "rejected"})
        return ReviewSummaryResponse(
            total=len(reviews),
            pending=sum(1 for item in reviews if item.status == "pending"),
            approved=sum(1 for item in reviews if item.status == "approved"),
            rejected=sum(1 for item in reviews if item.status == "rejected"),
            resolution_rate=round(resolved / len(reviews), 4) if reviews else 0.0,
            negative_rule_count=len(self.list_negative_rules()),
        )

    def grouped(self, group_by: str) -> ReviewGroupedResponse:
        allowed = {
            "schema_id",
            "target_field",
            "review_required_reason",
            "confidence_tier",
            "risk_flag",
            "source_label",
        }
        if group_by not in allowed:
            raise ValueError("unsupported review grouping")
        groups: dict[str, list[str]] = defaultdict(list)
        for review in self.workflow.list_reviews():
            for key in self._group_keys(review, group_by):
                groups[key].append(review.review_id)
        return ReviewGroupedResponse(
            group_by=group_by,
            items=[
                ReviewGroupItem(key=key, count=len(ids), review_ids=ids)
                for key, ids in sorted(groups.items())
            ],
        )

    def _validate_batch(self, reviews: list[ReviewRecord]) -> None:
        if not reviews:
            raise ValueError("batch review requires items")
        keys = {
            (
                item.source_field_name,
                item.target_field_id,
                item.schema_id,
                item.template_id,
            )
            for item in reviews
        }
        if len(keys) != 1:
            raise ValueError("batch approve requires identical mapping scope")
        if any(self._risk_flags(item) for item in reviews):
            raise ValueError("high-risk reviews cannot be batch approved")
        if any(self._badcase_hit(item) for item in reviews):
            raise ValueError("badcase-hit reviews cannot be batch approved")

    def _badcase_hit(self, review: ReviewRecord) -> bool:
        task = self.db.get(ConversionTask, review.task_id)
        if task is None:
            return False
        try:
            options = json.loads(task.options_json or "{}")
        except json.JSONDecodeError:
            return False
        for badcase in options.get("badcases", []):
            if not isinstance(badcase, dict):
                continue
            if badcase.get("source_field") != review.source_field_name:
                continue
            forbidden = badcase.get("forbidden_target_fields", [])
            if isinstance(forbidden, list) and review.target_field_id in forbidden:
                return True
        return False

    @staticmethod
    def _risk_flags(review: ReviewRecord) -> list[str]:
        reason = review.reason or ""
        marker = "risk_flags="
        if marker not in reason:
            return []
        value = reason.split(marker, 1)[1].split(";", 1)[0]
        return [item.strip() for item in value.split(",") if item.strip()]

    def _group_keys(self, review: ReviewRecord, group_by: str) -> list[str]:
        if group_by == "schema_id":
            return [review.schema_id or "unknown"]
        if group_by == "target_field":
            return [review.target_field_id or "unknown"]
        if group_by == "review_required_reason":
            return [review.reason or "unspecified"]
        if group_by == "confidence_tier":
            confidence = float(review.confidence or 0)
            return ["high" if confidence >= 0.8 else "medium" if confidence >= 0.5 else "low"]
        if group_by == "risk_flag":
            return self._risk_flags(review) or ["none"]
        return [review.source_field_name or "unknown"]
