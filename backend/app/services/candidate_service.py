import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ConversionTask, Document, FieldCandidateRecord
from app.engines.field_candidate_engine import FieldCandidateEngine
from app.schemas.mapping import FieldCandidate
from app.schemas.uir import UIRDocument
from app.services.storage_service import StorageService


class CandidateService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.engine = FieldCandidateEngine()

    def generate_candidates(
        self,
        task_id: str,
        include_metadata: bool = True,
        include_blocks: bool = True,
        include_tables: bool = True,
    ) -> list[FieldCandidate]:
        task = self._get_task(task_id)
        document = self._get_document(task.doc_id)
        uir = UIRDocument.model_validate(self.storage.read_json(document.storage_path))
        candidates = self.engine.extract(
            task_id=task_id,
            uir=uir,
            include_metadata=include_metadata,
            include_blocks=include_blocks,
            include_tables=include_tables,
        )

        self.db.query(FieldCandidateRecord).filter(FieldCandidateRecord.task_id == task_id).delete()
        for candidate in candidates:
            self.db.add(self._to_record(candidate))

        task.status = "candidates_ready"
        self.db.commit()
        return candidates

    def list_candidates(self, task_id: str) -> list[FieldCandidate]:
        self._get_task(task_id)
        records = (
            self.db.query(FieldCandidateRecord)
            .filter(FieldCandidateRecord.task_id == task_id)
            .order_by(FieldCandidateRecord.source_path.asc())
            .all()
        )
        return [self._from_record(record) for record in records]

    def _get_task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _get_document(self, doc_id: str) -> Document:
        document = self.db.get(Document, doc_id)
        if document is None:
            raise LookupError("document not found")
        return document

    @staticmethod
    def _to_record(candidate: FieldCandidate) -> FieldCandidateRecord:
        return FieldCandidateRecord(
            candidate_id=candidate.candidate_id,
            task_id=candidate.task_id,
            doc_id=candidate.doc_id,
            source_path=candidate.source_path,
            source_name=candidate.source_name,
            display_name=candidate.display_name,
            value_sample=json.dumps(candidate.value_sample, ensure_ascii=False),
            inferred_type=candidate.inferred_type,
            source_blocks_json=json.dumps(candidate.source_blocks, ensure_ascii=False),
            confidence=candidate.confidence,
        )

    @staticmethod
    def _from_record(record: FieldCandidateRecord) -> FieldCandidate:
        return FieldCandidate(
            candidate_id=record.candidate_id,
            task_id=record.task_id,
            doc_id=record.doc_id,
            source_path=record.source_path,
            source_name=record.source_name,
            display_name=record.display_name,
            value_sample=CandidateService._load_json_value(record.value_sample),
            inferred_type=record.inferred_type,
            source_blocks=json.loads(record.source_blocks_json or "[]"),
            confidence=record.confidence,
            evidence=[],
        )

    @staticmethod
    def _load_json_value(value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)
