import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ConversionTask,
    KnowledgeCandidateRecord,
    KnowledgePackItemRecord,
    KnowledgePackRecord,
    ReviewRecord,
)
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.services.effective_template_service import EffectiveTemplateService
from app.services.knowledge_service import KnowledgePack
from app.services.template_service import TemplateService


class ReviewKnowledgeWorkflowService:
    def __init__(
        self,
        db: Session,
        template_service: TemplateService | None = None,
    ) -> None:
        self.db = db
        self.template_service = template_service or TemplateService()

    def create_pending_reviews(
        self,
        *,
        task: ConversionTask,
        doc_id: str,
        mapping_report: MappingReport,
    ) -> list[ReviewRecord]:
        records: list[ReviewRecord] = []
        for item in mapping_report.review_required_items:
            mapping_id = str(item.get("mapping_id") or "")
            if not mapping_id:
                continue
            review_id = f"review_{task.task_id}_{mapping_id}"
            existing = self.db.get(ReviewRecord, review_id)
            if existing is not None:
                records.append(existing)
                continue
            source_field = item.get("source_field") if isinstance(item, dict) else {}
            source_field = source_field if isinstance(source_field, dict) else {}
            record = ReviewRecord(
                review_id=review_id,
                task_id=task.task_id,
                doc_id=doc_id,
                schema_id=task.schema_id,
                template_id=task.template_id,
                mapping_id=mapping_id,
                candidate_id=str(item.get("candidate_id") or ""),
                source_field_name=self._optional_str(source_field.get("source_name")),
                source_path=self._optional_str(source_field.get("source_path")),
                target_field_id=self._optional_str(item.get("target_field_id")),
                suggested_by=self._optional_str(item.get("method")),
                confidence=float(item["confidence"]) if "confidence" in item else None,
                reason="; ".join(str(value) for value in item.get("evidence", [])),
                status="pending",
                old_target_field_id=None,
                new_target_field_id=self._optional_str(item.get("target_field_id")),
                decision="pending",
                comment=None,
                review_comment=None,
                reviewer="system",
            )
            self.db.add(record)
            records.append(record)
        self.db.flush()
        return records

    def list_reviews(self, status: str | None = None) -> list[ReviewRecord]:
        statement = select(ReviewRecord).order_by(ReviewRecord.created_at.desc())
        if status:
            statement = statement.where(ReviewRecord.status == status)
        return list(self.db.scalars(statement))

    def get_review(self, review_id: str) -> ReviewRecord:
        record = self.db.get(ReviewRecord, review_id)
        if record is None:
            raise LookupError("review not found")
        return record

    def approve_review(
        self,
        review_id: str,
        *,
        reviewer: str,
        comment: str | None,
        create_knowledge_candidate: bool,
    ) -> tuple[ReviewRecord, KnowledgeCandidateRecord | None]:
        record = self.get_review(review_id)
        record.status = "approved"
        record.decision = "approved"
        record.reviewer = reviewer
        record.comment = comment
        record.review_comment = comment
        record.updated_at = self._now()
        candidate = None
        if create_knowledge_candidate:
            candidate = self._create_candidate(record)
        self.db.commit()
        self.db.refresh(record)
        if candidate is not None:
            self.db.refresh(candidate)
        return record, candidate

    def reject_review(
        self,
        review_id: str,
        *,
        reviewer: str,
        comment: str | None,
    ) -> ReviewRecord:
        record = self.get_review(review_id)
        record.status = "rejected"
        record.decision = "rejected"
        record.reviewer = reviewer
        record.comment = comment
        record.review_comment = comment
        record.updated_at = self._now()
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_candidates(self, status: str | None = None) -> list[KnowledgeCandidateRecord]:
        statement = select(KnowledgeCandidateRecord).order_by(
            KnowledgeCandidateRecord.created_at.desc()
        )
        if status:
            statement = statement.where(KnowledgeCandidateRecord.status == status)
        return list(self.db.scalars(statement))

    def accept_candidate(self, candidate_id: str) -> KnowledgeCandidateRecord:
        return self._set_candidate_status(candidate_id, "accepted")

    def reject_candidate(self, candidate_id: str) -> KnowledgeCandidateRecord:
        return self._set_candidate_status(candidate_id, "rejected")

    def list_packs(self, status: str | None = None) -> list[KnowledgePackRecord]:
        statement = select(KnowledgePackRecord).order_by(KnowledgePackRecord.created_at.desc())
        if status:
            statement = statement.where(KnowledgePackRecord.status == status)
        return list(self.db.scalars(statement))

    def create_pack(
        self,
        *,
        schema_id: str,
        template_id: str,
        name: str | None,
        created_by: str,
    ) -> KnowledgePackRecord:
        accepted = self.list_candidates("accepted")
        candidates = [
            candidate
            for candidate in accepted
            if candidate.schema_id == schema_id and candidate.template_id == template_id
        ]
        pack_id = f"kp_{schema_id}_{template_id}_{len(self.list_packs()) + 1}"
        pack = KnowledgePackRecord(
            pack_id=pack_id,
            name=name or f"{schema_id} {template_id} pack",
            schema_id=schema_id,
            template_id=template_id,
            version="1.0.0",
            status="draft",
            created_by=created_by,
            metadata_json=json.dumps(
                {"candidate_count": len(candidates)},
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        self.db.add(pack)
        for index, candidate in enumerate(candidates, start=1):
            self.db.add(
                KnowledgePackItemRecord(
                    item_id=f"{pack_id}_item_{index}",
                    pack_id=pack_id,
                    item_type=candidate.candidate_type,
                    target_field_id=candidate.target_field_id,
                    value_json=json.dumps(
                        {"alias": candidate.alias},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    candidate_id=candidate.candidate_id,
                )
            )
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def activate_pack(self, pack_id: str) -> KnowledgePackRecord:
        pack = self._get_pack(pack_id)
        pack.status = "active"
        pack.activated_at = self._now()
        pack.updated_at = self._now()
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def archive_pack(self, pack_id: str) -> KnowledgePackRecord:
        pack = self._get_pack(pack_id)
        pack.status = "archived"
        pack.updated_at = self._now()
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def effective_template(self, schema_id: str, template_id: str) -> MappingTemplate:
        base_template = self.template_service.load_template(template_id)
        if base_template.schema_id != schema_id:
            raise ValueError("template does not belong to schema")
        packs = self.active_knowledge_packs(schema_id=schema_id, template_id=template_id)
        return EffectiveTemplateService().resolve(base_template, packs).template

    def active_knowledge_packs(
        self,
        *,
        schema_id: str,
        template_id: str,
    ) -> list[KnowledgePack]:
        packs = [
            pack
            for pack in self.list_packs("active")
            if pack.schema_id == schema_id and pack.template_id == template_id
        ]
        return [self._knowledge_pack_from_record(pack) for pack in packs]

    def metrics(self) -> dict[str, int]:
        reviews = self.list_reviews()
        candidates = self.list_candidates()
        packs = self.list_packs()
        return {
            "pending_reviews": sum(1 for record in reviews if record.status == "pending"),
            "approved_reviews": sum(1 for record in reviews if record.status == "approved"),
            "rejected_reviews": sum(1 for record in reviews if record.status == "rejected"),
            "pending_candidates": sum(
                1 for candidate in candidates if candidate.status == "pending"
            ),
            "accepted_candidates": sum(
                1 for candidate in candidates if candidate.status == "accepted"
            ),
            "rejected_candidates": sum(
                1 for candidate in candidates if candidate.status == "rejected"
            ),
            "blocked_candidates": sum(
                1 for candidate in candidates if candidate.status == "blocked"
            ),
            "draft_packs": sum(1 for pack in packs if pack.status == "draft"),
            "active_packs": sum(1 for pack in packs if pack.status == "active"),
            "archived_packs": sum(1 for pack in packs if pack.status == "archived"),
        }

    def pack_items(self, pack_id: str) -> list[KnowledgePackItemRecord]:
        return list(
            self.db.scalars(
                select(KnowledgePackItemRecord)
                .where(KnowledgePackItemRecord.pack_id == pack_id)
                .order_by(KnowledgePackItemRecord.created_at)
            )
        )

    def _create_candidate(self, record: ReviewRecord) -> KnowledgeCandidateRecord | None:
        if not all(
            [
                record.schema_id,
                record.template_id,
                record.target_field_id,
                record.source_field_name,
            ]
        ):
            return None
        candidate_id = f"kc_{record.review_id}"
        existing = self.db.get(KnowledgeCandidateRecord, candidate_id)
        if existing is not None:
            return existing
        badcase_hit = self._badcase_hit(record)
        candidate = KnowledgeCandidateRecord(
            candidate_id=candidate_id,
            review_id=record.review_id,
            schema_id=str(record.schema_id),
            template_id=str(record.template_id),
            target_field_id=str(record.target_field_id),
            alias=str(record.source_field_name),
            candidate_type="alias",
            support_count=1,
            badcase_hit=badcase_hit,
            status="blocked" if badcase_hit else "pending",
        )
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def _badcase_hit(self, record: ReviewRecord) -> bool:
        task = self.db.get(ConversionTask, record.task_id)
        if task is None:
            return False
        try:
            options = json.loads(task.options_json or "{}")
        except json.JSONDecodeError:
            return False
        badcases = options.get("badcases", [])
        if not isinstance(badcases, list):
            return False
        for badcase in badcases:
            if not isinstance(badcase, dict):
                continue
            if badcase.get("source_field") != record.source_field_name:
                continue
            forbidden = badcase.get("forbidden_target_fields", [])
            if isinstance(forbidden, list) and record.target_field_id in forbidden:
                return True
        return False

    def _set_candidate_status(
        self,
        candidate_id: str,
        status: str,
    ) -> KnowledgeCandidateRecord:
        candidate = self.db.get(KnowledgeCandidateRecord, candidate_id)
        if candidate is None:
            raise LookupError("knowledge candidate not found")
        if candidate.status == "blocked":
            raise ValueError("blocked candidate cannot change status")
        candidate.status = status
        candidate.updated_at = self._now()
        self.db.commit()
        self.db.refresh(candidate)
        return candidate

    def _get_pack(self, pack_id: str) -> KnowledgePackRecord:
        pack = self.db.get(KnowledgePackRecord, pack_id)
        if pack is None:
            raise LookupError("knowledge pack not found")
        return pack

    def _knowledge_pack_from_record(self, pack: KnowledgePackRecord) -> KnowledgePack:
        aliases: dict[str, list[str]] = {}
        for item in self.pack_items(pack.pack_id):
            if item.item_type != "alias":
                continue
            try:
                value = json.loads(item.value_json)
            except json.JSONDecodeError:
                continue
            alias = value.get("alias")
            if not isinstance(alias, str):
                continue
            aliases.setdefault(item.target_field_id, [])
            if alias not in aliases[item.target_field_id]:
                aliases[item.target_field_id].append(alias)
        return KnowledgePack(
            pack_id=pack.pack_id,
            schema_id=pack.schema_id,
            template_id=pack.template_id,
            aliases={key: sorted(values) for key, values in sorted(aliases.items())},
            status=pack.status,
            candidate_ids=[
                item.candidate_id
                for item in self.pack_items(pack.pack_id)
                if item.candidate_id
            ],
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
