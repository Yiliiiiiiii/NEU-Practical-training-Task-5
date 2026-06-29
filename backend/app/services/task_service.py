import json

from sqlalchemy.orm import Session

from app.db.models import ConversionTask, Document
from app.schemas.api import TaskCreateRequest
from app.services.storage_service import StorageService
from app.utils.ids import new_id
from app.utils.redaction import redact_sensitive_values


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
            options_json=json.dumps(
                redact_sensitive_values(request.options),
                ensure_ascii=False,
                sort_keys=True,
            ),
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

    @staticmethod
    def task_options(task: ConversionTask) -> dict:
        parsed = json.loads(task.options_json or "{}")
        if not isinstance(parsed, dict):
            return {}
        return redact_sensitive_values(parsed)
