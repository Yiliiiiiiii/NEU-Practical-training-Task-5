import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ConversionTask, Document
from app.schemas.reports import MappingReport
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.canonical_service import CanonicalService
from app.services.catalog_governance_service import CatalogGovernanceService
from app.services.chunk_organizer_service import ChunkOrganizerService
from app.services.effective_template_service import EffectiveTemplateService
from app.services.mapping_service import MappingService
from app.services.package_service import PackageService
from app.services.render_service import RenderedArtifacts, RenderService
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService
from app.services.schema_service import SchemaService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService
from app.services.template_service import TemplateService
from app.services.transform_service import TransformService
from app.services.validation_service import ValidationService


@dataclass(frozen=True)
class TaskExecutionResult:
    task_id: str
    status: str
    report_paths: dict[str, str] = field(default_factory=dict)
    package_zip_path: str | None = None
    review_required_count: int = 0
    unmapped_required_count: int = 0


class TaskExecutionService:
    REPORT_KEYS = {
        "mapping": "mapping_report",
        "validation": "validation_report",
        "transform": "transform_report",
        "canonical": "canonical",
        "content": "content_json",
        "chunks": "chunks",
        "verifier": "verifier_report",
        "content_organization": "content_organization_report",
        "content-organization": "content_organization_report",
    }

    def __init__(
        self,
        db: Session,
        storage: StorageService,
        schema_service: SchemaService | None = None,
        template_service: TemplateService | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.schema_service = schema_service or SchemaService()
        self.template_service = template_service or TemplateService()

    def execute_task(self, task_id: str) -> TaskExecutionResult:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")

        task.started_at = self._now()
        task.finished_at = None
        task.status = "running"
        task.error_code = None
        task.error_message = None
        self.db.commit()

        try:
            return self._execute(task)
        except LookupError as exc:
            self._mark_failed(task, "lookup_error", str(exc))
            raise
        except ValueError as exc:
            self._mark_failed(task, "validation_error", str(exc))
            raise
        except Exception as exc:
            self._mark_failed(task, "execution_error", str(exc))
            raise

    def execution_snapshot(self, task: ConversionTask) -> dict[str, Any]:
        if not task.config_snapshot_path:
            return {}
        try:
            snapshot = self.storage.read_json(task.config_snapshot_path)
        except (FileNotFoundError, ValueError):
            return {}
        return snapshot if isinstance(snapshot, dict) else {}

    def read_report(self, task_id: str, report_name: str) -> dict[str, Any]:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        snapshot = self.execution_snapshot(task)
        report_key = self.REPORT_KEYS.get(report_name)
        if report_key is None:
            raise LookupError("report not found")
        report_paths = snapshot.get("report_paths", {})
        if not isinstance(report_paths, dict) or report_key not in report_paths:
            raise LookupError("report not found")
        return self._read_storage_json_path(str(report_paths[report_key]))

    def package_metadata(self, task_id: str) -> dict[str, Any]:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        snapshot = self.execution_snapshot(task)
        report_paths = snapshot.get("report_paths", {})
        if not isinstance(report_paths, dict) or "package_metadata" not in report_paths:
            raise LookupError("package not found")
        metadata = self._read_storage_json_path(str(report_paths["package_metadata"]))
        metadata.setdefault("zip_path", snapshot.get("package_zip_path"))
        return metadata

    def package_zip_path(self, task_id: str) -> Path:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        snapshot = self.execution_snapshot(task)
        package_zip_path = snapshot.get("package_zip_path")
        if not isinstance(package_zip_path, str):
            raise LookupError("package not found")
        path = self._safe_storage_path(package_zip_path)
        if not path.is_file():
            raise LookupError("package not found")
        return path

    def _execute(self, task: ConversionTask) -> TaskExecutionResult:
        document = self.db.get(Document, task.doc_id)
        if document is None:
            raise LookupError("document not found")

        uir_data = self.storage.read_json(document.storage_path)
        uir = UIRDocument.model_validate(uir_data)
        options = TaskService.task_options(task)
        catalog_service = CatalogGovernanceService(
            self.db,
            self.schema_service,
            self.template_service,
        )

        try:
            schema = catalog_service.load_schema(task.schema_id, task.schema_version)
        except LookupError as exc:
            raise LookupError(f"schema not found: {task.schema_id}") from exc

        try:
            template = catalog_service.load_template(
                task.template_id,
                task.template_version,
            )
        except LookupError as exc:
            raise LookupError(f"template not found: {task.template_id}") from exc
        self.template_service.validate_template(template, schema)
        review_knowledge_service = ReviewKnowledgeWorkflowService(
            self.db,
            self.template_service,
        )
        active_packs = review_knowledge_service.active_knowledge_packs(
            schema_id=schema.schema_id,
            template_id=template.template_id,
        )
        effective_result = EffectiveTemplateService().resolve(template, active_packs)
        template = effective_result.template

        candidates = CandidateService().extract_candidates(task.task_id, uir)
        mapping_report = MappingService().map_fields(
            task_id=task.task_id,
            uir=uir,
            schema=schema,
            template=template,
            candidates=candidates,
            options=options,
        )
        review_knowledge_service.create_pending_reviews(
            task=task,
            doc_id=document.doc_id,
            mapping_report=mapping_report,
        )
        transform_result = TransformService().transform(
            task_id=task.task_id,
            uir=uir,
            schema=schema,
            template=template,
            mapping_report=mapping_report,
        )

        started_at = (task.started_at or self._now()).isoformat()
        execution_snapshot = {
            "task_id": task.task_id,
            "doc_id": document.doc_id,
            "schema_id": task.schema_id,
            "schema_version": task.schema_version,
            "template_id": task.template_id,
            "template_version": task.template_version,
            "applied_knowledge_pack_ids": effective_result.applied_pack_ids,
            "input_hash": task.input_hash,
            "options": options,
            "started_at": started_at,
        }
        canonical = CanonicalService().build_canonical(
            task_id=task.task_id,
            uir=uir,
            schema=schema,
            template=template,
            transform_result=transform_result,
            mapping_report=mapping_report,
            execution_snapshot=execution_snapshot,
        )
        rendered = RenderService().render(
            canonical,
            chunk_size=int(options.get("chunk_size", 1200)),
        )
        preliminary_validation_report = ValidationService().validate(
            task.task_id,
            schema,
            rendered,
        )
        organized_chunks, content_organization_report = ChunkOrganizerService().organize_chunks(
            chunks=rendered.chunks,
            canonical_model=canonical,
            schema=schema,
            mapping_report=mapping_report,
            validation_report=preliminary_validation_report,
            task_id=task.task_id,
            doc_id=document.doc_id,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            template_version=template.version,
        )
        rendered = RenderedArtifacts(
            structured_json=rendered.structured_json,
            markdown=rendered.markdown,
            chunks=organized_chunks,
        )
        validation_report = ValidationService().validate(
            task.task_id,
            schema,
            rendered,
            require_content_organization=True,
        )
        package_result = PackageService(self.storage.root).create_package(
            task_id=task.task_id,
            doc_id=document.doc_id,
            schema=schema,
            template=template,
            canonical=canonical,
            rendered=rendered,
            mapping_report=mapping_report,
            transform_report=transform_result.report,
            validation_report=validation_report,
            content_organization_report=content_organization_report,
        )

        report_paths = self._write_execution_artifacts(
            task_id=task.task_id,
            mapping_report=mapping_report,
            transform_report=transform_result.report,
            canonical=canonical.model_dump(mode="json"),
            rendered=rendered.structured_json,
            chunks=rendered.chunks,
            validation_report=validation_report.model_dump(mode="json"),
            content_organization_report=content_organization_report.model_dump(mode="json"),
            package_metadata=package_result.metadata.model_dump(mode="json"),
            verifier_report=package_result.verifier_report.model_dump(mode="json"),
        )
        finished_at = self._now()
        review_required_count = len(mapping_report.review_required_items)
        unmapped_required_count = sum(
            1 for item in mapping_report.unmapped if item.get("required")
        )
        status = self._final_status(
            package_passed=package_result.verifier_report.passed,
            review_required_count=review_required_count,
            unmapped_required_count=unmapped_required_count,
        )
        snapshot_path = f"tasks/{task.task_id}/execution_snapshot.json"
        execution_snapshot.update(
            {
                "status": status,
                "finished_at": finished_at.isoformat(),
                "report_paths": report_paths,
                "package_zip_path": package_result.metadata.zip_path,
                "review_required_count": review_required_count,
                "unmapped_required_count": unmapped_required_count,
                "validation_passed": validation_report.passed,
                "package_verifier_passed": package_result.verifier_report.passed,
            }
        )
        self.storage.save_json(snapshot_path, execution_snapshot)

        task.status = status
        task.config_snapshot_path = snapshot_path
        task.finished_at = finished_at
        task.updated_at = finished_at
        task.error_code = None if status != "failed" else "package_verification_failed"
        task.error_message = None if status != "failed" else "package verification failed"
        self.db.commit()
        self.db.refresh(task)

        return TaskExecutionResult(
            task_id=task.task_id,
            status=status,
            report_paths=report_paths,
            package_zip_path=package_result.metadata.zip_path,
            review_required_count=review_required_count,
            unmapped_required_count=unmapped_required_count,
        )

    def _write_execution_artifacts(
        self,
        task_id: str,
        mapping_report: MappingReport,
        transform_report: dict[str, Any],
        canonical: dict[str, Any],
        rendered: dict[str, Any],
        chunks: list[dict[str, Any]],
        validation_report: dict[str, Any],
        content_organization_report: dict[str, Any],
        package_metadata: dict[str, Any],
        verifier_report: dict[str, Any],
    ) -> dict[str, str]:
        base = f"tasks/{task_id}"
        return {
            "mapping_report": str(
                self.storage.save_json(
                    f"{base}/mapping_report.json",
                    mapping_report.model_dump(mode="json"),
                )
            ),
            "transform_report": str(
                self.storage.save_json(f"{base}/transform_report.json", transform_report)
            ),
            "canonical": str(self.storage.save_json(f"{base}/canonical.json", canonical)),
            "content_json": str(self.storage.save_json(f"{base}/content.json", rendered)),
            "chunks": str(
                self.storage.save_json(
                    f"{base}/chunks.json",
                    {"items": chunks, "total": len(chunks)},
                )
            ),
            "validation_report": str(
                self.storage.save_json(f"{base}/validation_report.json", validation_report)
            ),
            "content_organization_report": str(
                self.storage.save_json(
                    f"{base}/content_organization_report.json",
                    content_organization_report,
                )
            ),
            "package_metadata": str(
                self.storage.save_json(f"{base}/package_metadata.json", package_metadata)
            ),
            "verifier_report": str(
                self.storage.save_json(f"{base}/verifier_report.json", verifier_report)
            ),
        }

    @staticmethod
    def _final_status(
        package_passed: bool,
        review_required_count: int,
        unmapped_required_count: int,
    ) -> str:
        if not package_passed:
            return "failed"
        if review_required_count or unmapped_required_count:
            return "review_required"
        return "completed"

    def _mark_failed(self, task: ConversionTask, error_code: str, message: str) -> None:
        now = self._now()
        task.status = "failed"
        task.error_code = error_code
        task.error_message = message
        task.finished_at = now
        task.updated_at = now
        self.db.commit()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    def _read_storage_json_path(self, path_text: str) -> dict[str, Any]:
        path = self._safe_storage_path(path_text)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("stored report must be a JSON object")
        return data

    def _safe_storage_path(self, path_text: str) -> Path:
        path = Path(path_text)
        resolved = path.resolve() if path.is_absolute() else self.storage.resolve(path).resolve()
        if self.storage.root != resolved and self.storage.root not in resolved.parents:
            raise ValueError("unsafe storage path")
        return resolved
