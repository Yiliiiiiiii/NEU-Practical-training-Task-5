from sqlalchemy.orm import Session

from app.db.models import CanonicalModelRecord, ConversionTask
from app.renderers.chunks_renderer import ChunksRenderer
from app.renderers.json_renderer import JSONRenderer
from app.renderers.markdown_renderer import MarkdownRenderer
from app.schemas.canonical import CanonicalModel
from app.services.storage_service import StorageService
from app.services.trace_service import TraceService


class RenderService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.json_renderer = JSONRenderer()
        self.md_renderer = MarkdownRenderer()
        self.chunks_renderer = ChunksRenderer()

    def render_all(
        self,
        task_id: str,
        chunk_size: int = 500,
    ) -> list[str]:
        canonical = self._load_canonical(task_id)
        task = self._get_task(task_id)

        schema_version = task.schema_version

        content_json = self.json_renderer.render(canonical, schema_version)
        content_md = self.md_renderer.render(canonical)
        chunks_json = self.chunks_renderer.render(canonical, chunk_size=chunk_size)

        output_paths = [
            f"tasks/{task_id}/content.json",
            f"tasks/{task_id}/content.md",
            f"tasks/{task_id}/chunks.json",
        ]
        try:
            self.storage.save_json(
                output_paths[0],
                content_json.model_dump(mode="json"),
            )
            self.storage.write_text(output_paths[1], content_md)
            self.storage.save_json(
                output_paths[2],
                chunks_json.model_dump(mode="json"),
            )
        except Exception as exc:
            for path in output_paths:
                self.storage.resolve(path).unlink(missing_ok=True)
            task.status = "failed"
            task.error_code = "render_io_error"
            task.error_message = "failed to publish render outputs"
            TraceService(self.db, self.storage).record_event(
                task_id=task_id,
                stage="render",
                action="render_outputs",
                reason=str(exc),
                status="failed",
            )
            self.db.commit()
            raise

        TraceService(self.db, self.storage).record_batch(
            task_id,
            [
                {
                    "stage": "render",
                    "action": "render_content_json",
                    "source": {"canonical_task_id": canonical.task_id},
                    "result": {"path": "content.json"},
                    "reason": "rendered content.json from canonical model",
                    "status": "success",
                },
                {
                    "stage": "render",
                    "action": "render_content_markdown",
                    "source": {"canonical_task_id": canonical.task_id},
                    "result": {"path": "content.md"},
                    "reason": "rendered content.md from canonical model",
                    "status": "success",
                },
                {
                    "stage": "render",
                    "action": "render_chunks_json",
                    "source": {"canonical_task_id": canonical.task_id},
                    "result": {"path": "chunks.json"},
                    "reason": "rendered chunks.json from canonical model",
                    "status": "success",
                },
            ],
        )
        task.status = "rendered"
        task.error_code = None
        task.error_message = None
        self.db.commit()

        return ["content.json", "content.md", "chunks.json"]

    def _load_canonical(self, task_id: str) -> CanonicalModel:
        record = self.db.get(CanonicalModelRecord, task_id)
        if record is None:
            raise LookupError("canonical model not found")
        return CanonicalModel.model_validate_json(record.model_json)

    def _get_task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task
