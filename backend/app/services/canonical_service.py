import json

from sqlalchemy.orm import Session

from app.db.models import (
    CanonicalModelRecord,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
)
from app.engines.canonical_builder import CanonicalBuilder
from app.engines.transform_engine import TransformEngine
from app.schemas.canonical import CanonicalModel
from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.storage_service import StorageService
from app.services.trace_service import TraceService

BLOCKED_STATUSES = {"review_required", "failed", "cancelled"}


class CanonicalService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.builder = CanonicalBuilder()
        self.transform_engine = TransformEngine()

    def build_canonical(
        self,
        task_id: str,
        target_schema: TargetSchema,
        template: MappingTemplate,
    ) -> CanonicalModel:
        task = self._get_task(task_id)

        if task.status in BLOCKED_STATUSES:
            raise ValueError(
                f"cannot build canonical: task status is '{task.status}'"
            )

        document = self._get_document(task.doc_id)
        uir = UIRDocument.model_validate(self.storage.read_json(document.storage_path))

        if task.schema_id != target_schema.schema_id:
            raise ValueError(
                f"cannot build canonical: schema_id mismatch "
                f"(task={task.schema_id}, provided={target_schema.schema_id})"
            )
        if task.template_id != template.template_id:
            raise ValueError(
                f"cannot build canonical: template_id mismatch "
                f"(task={task.template_id}, provided={template.template_id})"
            )

        mappings = self._load_confirmed_mappings(task_id)
        unresolved_mappings = [
            mapping
            for mapping in mappings
            if mapping.need_review or mapping.status != "confirmed"
        ]
        if unresolved_mappings:
            raise ValueError("cannot build canonical: unresolved mapping requires review")

        candidates = self._load_candidates(task_id)
        source_context = {}
        for candidate in candidates:
            source_context[candidate.source_path] = candidate
            source_context[candidate.candidate_id] = candidate

        fields, trace_events, errors = self.transform_engine.execute(
            uir=uir,
            mappings=mappings,
            transform_rules=template.transform_rules,
            enum_maps=template.enum_maps,
            defaults=template.defaults,
            source_context=source_context,
        )

        for field in target_schema.fields:
            transformed_field = fields.get(field.field_id)
            if field.required and (
                transformed_field is None or transformed_field.value is None
            ):
                raise ValueError(
                    f"cannot build canonical: required field "
                    f"'{field.field_id}' has no mapping or default"
                )

        canonical = self.builder.build(
            task_id=task_id,
            doc_id=task.doc_id,
            schema_id=task.schema_id,
            fields=fields,
            uir=uir,
        )

        self.storage.save_json(
            f"tasks/{task_id}/canonical_model.json",
            canonical.model_dump(mode="json"),
        )

        self.db.query(CanonicalModelRecord).filter(
            CanonicalModelRecord.task_id == task_id
        ).delete()
        record = CanonicalModelRecord(
            task_id=task_id,
            doc_id=task.doc_id,
            schema_id=task.schema_id,
            model_json=canonical.model_dump_json(),
            storage_path=f"tasks/{task_id}/canonical_model.json",
        )
        self.db.add(record)

        trace_service = TraceService(self.db, self.storage)
        trace_service.record_batch(task_id, trace_events)
        self.db.commit()

        return canonical

    def get_canonical(self, task_id: str) -> CanonicalModel:
        record = self.db.get(CanonicalModelRecord, task_id)
        if record is None:
            raise LookupError("canonical model not found")
        return CanonicalModel.model_validate_json(record.model_json)

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

    def _load_confirmed_mappings(self, task_id: str) -> list[FieldMapping]:
        records = (
            self.db.query(FieldMappingRecord)
            .filter(FieldMappingRecord.task_id == task_id)
            .all()
        )
        mappings = []
        for record in records:
            candidate = self.db.get(FieldCandidateRecord, record.candidate_id)
            source_path = candidate.source_path if candidate else ""
            source_name = candidate.source_name if candidate else ""
            mappings.append(
                FieldMapping(
                    mapping_id=record.mapping_id,
                    task_id=record.task_id,
                    candidate_id=record.candidate_id,
                    source_field={"source_path": source_path, "source_name": source_name},
                    target_field_id=record.target_field_id,
                    target_field_name=record.target_field_id,
                    method=record.method,
                    confidence=record.confidence,
                    status=record.status,
                    need_review=record.need_review,
                    evidence=json.loads(record.evidence_json or "[]"),
                )
            )
        return mappings

    def _load_candidates(self, task_id: str) -> list[FieldCandidate]:
        return CandidateService(self.db, self.storage).list_candidates(task_id)
