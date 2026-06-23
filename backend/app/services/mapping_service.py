import json

from sqlalchemy.orm import Session

from app.clients.llm_client import LLMClient
from app.db.models import (
    ConversionTask,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.engines.mapping_engine import MappingEngine
from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.services.candidate_service import CandidateService
from app.services.storage_service import StorageService
from app.utils.ids import new_id


class MappingService:
    def __init__(
        self,
        db: Session,
        storage: StorageService,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.engine = MappingEngine()
        self.llm_client = llm_client or LLMClient(enabled=False, mode="disabled")

    def run_mapping(
        self,
        task_id: str,
        review_threshold: float,
        enable_llm_fallback: bool = False,
    ) -> tuple[list[FieldMapping], MappingReport, str]:
        task = self._get_task(task_id)
        candidates = self._load_candidates(task_id)
        if not candidates:
            candidates = CandidateService(self.db, self.storage).generate_candidates(task_id)

        schema = self._load_schema(task.schema_id)
        template = self._load_template(task.template_id)
        mappings = self.engine.map_fields(
            task_id=task_id,
            candidates=candidates,
            target_schema=schema,
            template=template,
            review_threshold=review_threshold,
        )
        llm_audit = self._apply_llm_fallback(
            task_id=task_id,
            mappings=mappings,
            candidates=candidates,
            schema=schema,
            enable_llm_fallback=enable_llm_fallback,
        )

        self.db.query(FieldMappingRecord).filter(FieldMappingRecord.task_id == task_id).delete()
        for mapping in mappings:
            self.db.add(self._to_record(mapping))

        report = self._build_report(task_id, schema, mappings, llm_audit)
        self.storage.save_json(
            f"tasks/{task_id}/mapping_report.json",
            report.model_dump(mode="json"),
        )

        task.status = (
            "review_required"
            if report.summary["review_required"]
            else "mapping_completed"
        )
        self.db.commit()
        return mappings, report, task.status

    def list_mappings(self, task_id: str) -> list[FieldMapping]:
        self._get_task(task_id)
        records = (
            self.db.query(FieldMappingRecord)
            .filter(FieldMappingRecord.task_id == task_id)
            .order_by(FieldMappingRecord.target_field_id.asc())
            .all()
        )
        return [self._from_record(record) for record in records]

    def read_mapping_report(self, task_id: str) -> MappingReport:
        self._get_task(task_id)
        data = self.storage.read_json(f"tasks/{task_id}/mapping_report.json")
        return MappingReport.model_validate(data)

    def _get_task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _load_schema(self, schema_id: str) -> TargetSchema:
        record = self.db.get(TargetSchemaRecord, schema_id)
        if record is None:
            raise LookupError("schema not found")
        return TargetSchema.model_validate_json(record.schema_json)

    def _load_template(self, template_id: str) -> MappingTemplate:
        record = self.db.get(MappingTemplateRecord, template_id)
        if record is None:
            raise LookupError("template not found")
        return MappingTemplate.model_validate_json(record.template_json)

    def _load_candidates(self, task_id: str) -> list[FieldCandidate]:
        records = (
            self.db.query(FieldCandidateRecord)
            .filter(FieldCandidateRecord.task_id == task_id)
            .all()
        )
        return [CandidateService._from_record(record) for record in records]

    def _apply_llm_fallback(
        self,
        *,
        task_id: str,
        mappings: list[FieldMapping],
        candidates: list[FieldCandidate],
        schema: TargetSchema,
        enable_llm_fallback: bool,
    ) -> dict:
        if not enable_llm_fallback:
            return {
                "enabled": False,
                "mode": self.llm_client.mode,
                "model": self.llm_client.model,
                "prompt_version": self.llm_client.prompt_version,
                "status": "disabled",
                "suggestion_count": 0,
                "latency_ms": None,
                "error": None,
            }

        mapped_targets = {mapping.target_field_id for mapping in mappings}
        used_candidates = {mapping.candidate_id for mapping in mappings}
        target_by_id = {field.field_id: field for field in schema.fields}
        candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
        unmapped_targets = [
            field for field in schema.fields if field.field_id not in mapped_targets
        ]
        unused_candidates = [
            candidate for candidate in candidates if candidate.candidate_id not in used_candidates
        ]
        suggestions = self.llm_client.suggest_mappings(
            candidates=[candidate.model_dump(mode="json") for candidate in unused_candidates],
            target_fields=[field.model_dump(mode="json") for field in unmapped_targets],
        )
        for suggestion in suggestions:
            if suggestion.target_field_id in mapped_targets:
                continue
            candidate = candidate_by_id.get(suggestion.candidate_id)
            target = target_by_id.get(suggestion.target_field_id)
            if candidate is None or target is None or candidate.candidate_id in used_candidates:
                continue
            mappings.append(self._llm_mapping(task_id, candidate, target, suggestion))
            mapped_targets.add(target.field_id)
            used_candidates.add(candidate.candidate_id)
        return dict(self.llm_client.last_audit)

    @staticmethod
    def _llm_mapping(
        task_id: str,
        candidate: FieldCandidate,
        target: TargetField,
        suggestion,
    ) -> FieldMapping:
        return FieldMapping(
            mapping_id=new_id("map"),
            task_id=task_id,
            candidate_id=candidate.candidate_id,
            source_field={
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            target_field_id=target.field_id,
            target_field_name=target.name,
            method="llm_fallback",
            confidence=suggestion.confidence,
            status="review_required",
            need_review=True,
            evidence=[suggestion.reason],
        )

    def _build_report(
        self,
        task_id: str,
        schema: TargetSchema,
        mappings: list[FieldMapping],
        llm_audit: dict,
    ) -> MappingReport:
        mapped_targets = {mapping.target_field_id for mapping in mappings}
        unmapped = [
            field.field_id for field in schema.fields if field.field_id not in mapped_targets
        ]
        review_required = [mapping for mapping in mappings if mapping.need_review]
        avg_confidence = (
            sum(mapping.confidence for mapping in mappings) / len(mappings) if mappings else 0
        )
        return MappingReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            summary={
                "target_fields": len(schema.fields),
                "mapped_fields": len(mapped_targets),
                "unmapped_required_fields": len(
                    [
                        field
                        for field in schema.fields
                        if field.required and field.field_id in unmapped
                    ]
                ),
                "review_required": len(review_required),
                "average_confidence": round(avg_confidence, 3),
                "llm_enabled": bool(llm_audit.get("enabled")),
                "llm_mode": llm_audit.get("mode"),
                "llm_model": llm_audit.get("model"),
                "llm_prompt_version": llm_audit.get("prompt_version"),
                "llm_status": llm_audit.get("status"),
                "llm_suggestion_count": llm_audit.get("suggestion_count", 0),
                "llm_latency_ms": llm_audit.get("latency_ms"),
                "llm_error": llm_audit.get("error"),
            },
            mappings=[
                {
                    "source_name": mapping.source_field.source_name,
                    "target_field_id": mapping.target_field_id,
                    "method": mapping.method,
                    "confidence": mapping.confidence,
                    "need_review": mapping.need_review,
                    "evidence": mapping.evidence,
                }
                for mapping in mappings
            ],
            unmapped=unmapped,
            review_required_items=[
                {"mapping_id": mapping.mapping_id, "target_field_id": mapping.target_field_id}
                for mapping in review_required
            ],
        )

    @staticmethod
    def _to_record(mapping: FieldMapping) -> FieldMappingRecord:
        return FieldMappingRecord(
            mapping_id=mapping.mapping_id,
            task_id=mapping.task_id,
            candidate_id=mapping.candidate_id,
            target_field_id=mapping.target_field_id,
            method=mapping.method,
            confidence=mapping.confidence,
            status=mapping.status,
            need_review=mapping.need_review,
            evidence_json=json.dumps(mapping.evidence, ensure_ascii=False),
        )

    def _from_record(self, record: FieldMappingRecord) -> FieldMapping:
        candidate = self.db.get(FieldCandidateRecord, record.candidate_id)
        source_path = candidate.source_path if candidate else ""
        source_name = candidate.source_name if candidate else ""
        return FieldMapping(
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
