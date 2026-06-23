import json

from sqlalchemy.orm import Session

from app.db.models import (
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
)
from app.schemas.api import TaskCreateRequest, TaskReplayRequest
from app.services.storage_service import StorageService
from app.utils.ids import new_id


class TaskService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def create_task(self, request: TaskCreateRequest) -> ConversionTask:
        document = self.db.get(Document, request.doc_id)
        if document is None:
            raise LookupError("document not found")

        task = ConversionTask(
            task_id=new_id("task"),
            doc_id=document.doc_id,
            schema_id=request.schema_id,
            schema_version=request.schema_version,
            template_id=request.template_id,
            template_version=request.template_version,
            status="created",
            input_hash=f"sha256:{self.storage.sha256(document.storage_path)}",
            options_json=json.dumps(request.options, ensure_ascii=False, sort_keys=True),
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(self, page: int = 1, page_size: int = 20) -> tuple[list[ConversionTask], int]:
        query = self.db.query(ConversionTask)
        total = query.count()
        items = (
            query.order_by(ConversionTask.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_task(self, task_id: str) -> ConversionTask | None:
        return self.db.get(ConversionTask, task_id)

    def replay_task(
        self,
        parent_task_id: str,
        request: TaskReplayRequest,
    ) -> tuple[ConversionTask, dict[str, int]]:
        parent = self.get_task(parent_task_id)
        if parent is None:
            raise LookupError("parent task not found")

        options = self.task_options(parent)
        options.update(request.options_override)
        if not request.repeat_model_calls:
            options["enable_llm_fallback"] = False
        options["replay"] = {
            "parent_task_id": parent_task_id,
            "reuse_confirmed_mappings": request.reuse_confirmed_mappings,
            "repeat_model_calls": request.repeat_model_calls,
        }

        child = ConversionTask(
            task_id=new_id("task"),
            parent_task_id=parent.task_id,
            doc_id=parent.doc_id,
            schema_id=parent.schema_id,
            schema_version=parent.schema_version,
            template_id=parent.template_id,
            template_version=parent.template_version,
            status="created",
            input_hash=parent.input_hash,
            options_json=json.dumps(options, ensure_ascii=False, sort_keys=True),
        )
        self.db.add(child)
        self.db.flush()

        counts = {"candidates": 0, "mappings": 0}
        if request.reuse_confirmed_mappings:
            counts = self._copy_confirmed_mapping_state(parent.task_id, child.task_id)
            child.status = "mapping_completed"

        self.db.commit()
        self.db.refresh(child)
        return child, counts

    @staticmethod
    def task_options(task: ConversionTask) -> dict:
        parsed = json.loads(task.options_json or "{}")
        if not isinstance(parsed, dict):
            return {}
        return parsed

    def _copy_confirmed_mapping_state(
        self,
        parent_task_id: str,
        child_task_id: str,
    ) -> dict[str, int]:
        candidates = (
            self.db.query(FieldCandidateRecord)
            .filter(FieldCandidateRecord.task_id == parent_task_id)
            .all()
        )
        mappings = (
            self.db.query(FieldMappingRecord)
            .filter(
                FieldMappingRecord.task_id == parent_task_id,
                FieldMappingRecord.status == "confirmed",
                FieldMappingRecord.need_review.is_(False),
            )
            .all()
        )
        if not mappings:
            raise ValueError("parent task has no confirmed mappings to replay")

        candidate_id_map: dict[str, str] = {}
        for candidate in candidates:
            new_candidate_id = new_id("cand")
            candidate_id_map[candidate.candidate_id] = new_candidate_id
            self.db.add(FieldCandidateRecord(
                candidate_id=new_candidate_id,
                task_id=child_task_id,
                doc_id=candidate.doc_id,
                source_path=candidate.source_path,
                source_name=candidate.source_name,
                display_name=candidate.display_name,
                value_sample=candidate.value_sample,
                inferred_type=candidate.inferred_type,
                source_blocks_json=candidate.source_blocks_json,
                confidence=candidate.confidence,
            ))

        for mapping in mappings:
            new_candidate_id = candidate_id_map.get(mapping.candidate_id)
            if new_candidate_id is None:
                raise ValueError("confirmed mapping references missing candidate")
            self.db.add(FieldMappingRecord(
                mapping_id=new_id("map"),
                task_id=child_task_id,
                candidate_id=new_candidate_id,
                target_field_id=mapping.target_field_id,
                method=mapping.method,
                confidence=mapping.confidence,
                status="confirmed",
                need_review=False,
                evidence_json=mapping.evidence_json,
            ))
        return {"candidates": len(candidates), "mappings": len(mappings)}
