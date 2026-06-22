from sqlalchemy.orm import Session

from app.db.models import ConversionTask, MappingTemplateRecord, TargetSchemaRecord
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.services.canonical_service import CanonicalService
from app.services.render_service import RenderService
from app.services.storage_service import StorageService

CONVERTIBLE_STATUSES = {"mapping_completed", "transforming", "rendered"}


class ConversionService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage
        self.canonical_service = CanonicalService(db, storage)
        self.render_service = RenderService(db, storage)

    def convert(
        self,
        task_id: str,
        render_outputs: bool,
        chunk_size: int,
    ) -> tuple[str, list[str]]:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        retrying_render = task.status == "failed" and task.error_code == "render_io_error"
        if task.status not in CONVERTIBLE_STATUSES and not retrying_render:
            raise ValueError(f"task status '{task.status}' does not allow convert")
        if retrying_render:
            task.status = "mapping_completed"
            self.db.commit()

        schema_record = self.db.get(TargetSchemaRecord, task.schema_id)
        if schema_record is None:
            raise LookupError("schema not found")
        template_record = self.db.get(MappingTemplateRecord, task.template_id)
        if template_record is None:
            raise LookupError("template not found")

        target_schema = TargetSchema.model_validate_json(schema_record.schema_json)
        template = MappingTemplate.model_validate_json(template_record.template_json)
        self.canonical_service.build_canonical(task_id, target_schema, template)

        if not render_outputs:
            task.status = "transforming"
            task.error_code = None
            task.error_message = None
            self.db.commit()
            return task.status, []

        outputs = self.render_service.render_all(task_id, chunk_size=chunk_size)
        return "rendered", outputs
