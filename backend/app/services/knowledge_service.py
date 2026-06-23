import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    ConversionTask,
    FieldCandidateRecord,
    FieldMappingRecord,
    LearningCandidateRecord,
    RealRunRecord,
    ReviewRecord,
    TransformTraceRecord,
)
from app.schemas.knowledge import (
    LearningCandidateView,
    RealRunView,
)
from app.services.storage_service import StorageService
from app.utils.ids import new_id


class KnowledgeValidationError(ValueError):
    pass


class KnowledgeService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def capture_real_run(self, task_id: str) -> RealRunView:
        task = self._task(task_id)
        mapping_path = f"tasks/{task_id}/mapping_report.json"
        try:
            mapping_report = self.storage.read_json(mapping_path)
        except FileNotFoundError:
            mapping_report = {"summary": {}, "unmapped": []}
        summary = dict(mapping_report.get("summary", {}))
        report_paths = {"mapping_report": mapping_path}
        record = RealRunRecord(
            real_run_id=new_id("run"),
            task_id=task.task_id,
            doc_id=task.doc_id,
            schema_id=task.schema_id,
            template_id=task.template_id,
            input_hash=task.input_hash,
            status="captured",
            summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True),
            report_paths_json=json.dumps(report_paths, ensure_ascii=False, sort_keys=True),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._real_run_view(record)

    def derive_learning_candidates(self, real_run_id: str) -> list[LearningCandidateView]:
        run = self._real_run(real_run_id)
        existing = (
            self.db.query(LearningCandidateRecord)
            .filter(LearningCandidateRecord.real_run_id == real_run_id)
            .order_by(
                LearningCandidateRecord.created_at.asc(),
                LearningCandidateRecord.candidate_id.asc(),
            )
            .all()
        )
        if existing:
            return [self._candidate_view(record) for record in existing]

        created: list[LearningCandidateRecord] = []
        created.extend(self._review_alias_candidates(run))
        created.extend(self._trace_badcase_candidates(run))
        created.extend(self._unmapped_badcase_candidates(run))
        for record in created:
            self.db.add(record)
        self.db.commit()
        return [self._candidate_view(record) for record in created]

    def _review_alias_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        candidates: list[LearningCandidateRecord] = []
        reviews = (
            self.db.query(ReviewRecord)
            .filter(ReviewRecord.task_id == run.task_id)
            .order_by(ReviewRecord.created_at.asc())
            .all()
        )
        for review in reviews:
            if review.decision not in {"confirmed", "changed"}:
                continue
            mapping = self.db.get(FieldMappingRecord, review.mapping_id)
            if mapping is None or mapping.task_id != run.task_id:
                continue
            source = self.db.get(FieldCandidateRecord, mapping.candidate_id)
            if source is None:
                continue
            target = review.new_target_field_id or mapping.target_field_id
            if not target or not source.source_name:
                continue
            generator = (
                "llm_review_feedback" if mapping.method == "llm_fallback" else "review_feedback"
            )
            candidates.append(
                self._candidate_record(
                    run=run,
                    candidate_type="alias_candidate",
                    target_field_id=target,
                    proposed_payload={"aliases": [source.source_name]},
                    evidence={
                        "mapping_id": mapping.mapping_id,
                        "source_name": source.source_name,
                        "source_path": source.source_path,
                        "old_target_field_id": review.old_target_field_id,
                        "new_target_field_id": target,
                        "review_decision": review.decision,
                    },
                    generator=generator,
                    confidence=mapping.confidence,
                    risk_level="high" if mapping.method == "llm_fallback" else "medium",
                )
            )
        return candidates

    def _unmapped_badcase_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        paths = json.loads(run.report_paths_json or "{}")
        mapping_path = paths.get("mapping_report")
        if not mapping_path:
            return []
        try:
            report = self.storage.read_json(mapping_path)
        except FileNotFoundError:
            return []
        unmapped = [str(item) for item in report.get("unmapped", [])]
        if not unmapped:
            return []
        return [
            self._candidate_record(
                run=run,
                candidate_type="badcase_candidate",
                target_field_id=None,
                proposed_payload={"case_type": "unmapped_required"},
                evidence={"unmapped_required_fields": unmapped},
                generator="mapping_report",
                confidence=1.0,
                risk_level="high",
            )
        ]

    def _trace_badcase_candidates(self, run: RealRunRecord) -> list[LearningCandidateRecord]:
        traces = (
            self.db.query(TransformTraceRecord)
            .filter(
                TransformTraceRecord.task_id == run.task_id,
                TransformTraceRecord.status == "error",
            )
            .all()
        )
        return [
            self._candidate_record(
                run=run,
                candidate_type="badcase_candidate",
                target_field_id=trace.target_field_id,
                proposed_payload={"case_type": "transform_error"},
                evidence={
                    "trace_id": trace.trace_id,
                    "action": trace.action,
                    "rule_id": trace.rule_id,
                    "reason": trace.reason,
                },
                generator="transform_trace",
                confidence=1.0,
                risk_level="high",
            )
            for trace in traces
        ]

    def _candidate_record(
        self,
        *,
        run: RealRunRecord,
        candidate_type: str,
        target_field_id: str | None,
        proposed_payload: dict[str, Any],
        evidence: dict[str, Any],
        generator: str,
        confidence: float,
        risk_level: str,
    ) -> LearningCandidateRecord:
        return LearningCandidateRecord(
            candidate_id=new_id("lc"),
            real_run_id=run.real_run_id,
            task_id=run.task_id,
            candidate_type=candidate_type,
            status="pending",
            risk_level=risk_level,
            target_field_id=target_field_id,
            proposed_payload_json=json.dumps(proposed_payload, ensure_ascii=False, sort_keys=True),
            final_payload_json="{}",
            evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            generator=generator,
            confidence=confidence,
        )

    def _task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _real_run(self, real_run_id: str) -> RealRunRecord:
        run = self.db.get(RealRunRecord, real_run_id)
        if run is None:
            raise LookupError("real run not found")
        return run

    @staticmethod
    def _real_run_view(record: RealRunRecord) -> RealRunView:
        return RealRunView(
            real_run_id=record.real_run_id,
            task_id=record.task_id,
            doc_id=record.doc_id,
            schema_id=record.schema_id,
            template_id=record.template_id,
            input_hash=record.input_hash,
            status=record.status,
            summary=json.loads(record.summary_json or "{}"),
            report_paths=json.loads(record.report_paths_json or "{}"),
        )

    @staticmethod
    def _candidate_view(record: LearningCandidateRecord) -> LearningCandidateView:
        return LearningCandidateView(
            candidate_id=record.candidate_id,
            real_run_id=record.real_run_id,
            task_id=record.task_id,
            candidate_type=record.candidate_type,
            status=record.status,
            risk_level=record.risk_level,
            target_field_id=record.target_field_id,
            proposed_payload=json.loads(record.proposed_payload_json or "{}"),
            final_payload=json.loads(record.final_payload_json or "{}"),
            evidence=json.loads(record.evidence_json or "{}"),
            generator=record.generator,
            confidence=record.confidence,
        )
