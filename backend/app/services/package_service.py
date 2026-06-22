import json
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import (
    CanonicalModelRecord,
    ConsistencyReportRecord,
    ConversionTask,
    OutputPackageRecord,
    PackageFileRecord,
    TargetSchemaRecord,
    ValidationReportRecord,
)
from app.engines.manifest_engine import generate_manifest
from app.schemas.canonical import CanonicalModel
from app.schemas.target_schema import TargetSchema
from app.services.storage_service import StorageService
from app.services.trace_service import TraceService
from app.utils.ids import new_id
from app.validators.consistency_validator import validate_consistency
from app.validators.content_validator import validate_content_data


class PackageService:
    def __init__(self, db: Session, storage: StorageService) -> None:
        self.db = db
        self.storage = storage

    def create_package(
        self,
        task_id: str,
        package_version: str = "1.0.0",
    ) -> dict:
        task = self._get_task(task_id)
        if task.status in ("review_required", "failed", "cancelled"):
            raise ValueError(f"task status '{task.status}' does not allow packaging")

        content_json_path = f"tasks/{task_id}/content.json"
        content_md_path = f"tasks/{task_id}/content.md"
        chunks_path = f"tasks/{task_id}/chunks.json"

        for p in [content_json_path, content_md_path, chunks_path]:
            self.storage.resolve(p)

        content_json_data = self.storage.read_json(content_json_path)
        content_md_text = self.storage.read_text(content_md_path)
        chunks_data = self.storage.read_json(chunks_path)

        canonical_record = self.db.get(CanonicalModelRecord, task_id)
        if canonical_record is None:
            raise LookupError("canonical model not found")
        canonical = CanonicalModel.model_validate_json(canonical_record.model_json)

        from app.schemas.chunks import ChunksJSON
        from app.schemas.content import ContentJSON
        content_json = ContentJSON.model_validate(content_json_data)
        chunks = ChunksJSON.model_validate(chunks_data)

        schema_record = self.db.get(TargetSchemaRecord, task.schema_id)
        target_schema = TargetSchema.model_validate_json(schema_record.schema_json)

        validation_report = validate_content_data(
            task_id=task_id,
            schema_id=task.schema_id,
            data=content_json.data,
            target_schema=target_schema,
        )
        self.storage.save_json(
            f"tasks/{task_id}/validation_report.json",
            validation_report.model_dump(mode="json"),
        )
        self._persist_validation_report(task_id, validation_report)

        consistency_report = validate_consistency(
            task_id=task_id,
            content_json=content_json,
            content_md=content_md_text,
            chunks=chunks,
            canonical=canonical,
        )
        self.storage.save_json(
            f"tasks/{task_id}/consistency_report.json",
            consistency_report.model_dump(mode="json"),
        )
        self._persist_consistency_report(task_id, consistency_report)

        if not consistency_report.passed:
            task.status = "failed"
            task.error_code = "consistency_critical"
            task.error_message = "consistency report has critical errors"
            self.db.commit()
            raise ValueError("consistency report has critical errors, packaging blocked")

        self._generate_metadata(task)
        self._generate_config_snapshot(task)
        self._ensure_mapping_report(task_id)
        self._ensure_trace(task_id)

        package_id = new_id("pkg")
        zip_path = f"packages/{package_id}/standard_package.zip"

        with tempfile.TemporaryDirectory() as tmpdir:
            staging = Path(tmpdir) / "staging"
            staging.mkdir()

            payload_files = [
                "content.json", "content.md", "chunks.json",
                "metadata.json", "config_snapshot.json",
                "mapping_report.json", "validation_report.json",
                "consistency_report.json", "trace.json",
            ]
            for fname in payload_files:
                src = self.storage.resolve(f"tasks/{task_id}/{fname}")
                if src.exists():
                    shutil.copy2(src, staging / fname)

            assets_dir = self.storage.resolve(f"tasks/{task_id}/assets")
            if assets_dir.exists():
                dest_assets = staging / "assets"
                shutil.copytree(assets_dir, dest_assets)

            manifest = generate_manifest(
                task_id=task_id,
                doc_id=task.doc_id,
                package_id=package_id,
                staging_dir=staging,
                package_version=package_version,
            )
            self.storage.save_json(
                f"tasks/{task_id}/manifest.json",
                manifest.model_dump(mode="json"),
            )
            shutil.copy2(
                self.storage.resolve(f"tasks/{task_id}/manifest.json"),
                staging / "manifest.json",
            )

            zip_dest = self.storage.resolve(zip_path)
            zip_dest.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(staging.rglob("*")):
                    if f.is_dir():
                        continue
                    arcname = f.relative_to(staging).as_posix()
                    zf.write(f, arcname)

            zip_sha256 = self.storage.sha256(zip_path)

            record = OutputPackageRecord(
                package_id=package_id,
                task_id=task_id,
                doc_id=task.doc_id,
                zip_path=zip_path,
                sha256=zip_sha256,
                status="completed",
            )
            self.db.add(record)

            for f in manifest.files:
                self.db.add(PackageFileRecord(
                    file_id=new_id("pfile"),
                    package_id=package_id,
                    relative_path=f.path,
                    media_type=f.media_type,
                    bytes=f.bytes,
                    sha256=f.sha256,
                ))

            task.status = "completed"
            self.db.commit()

        return {
            "package_id": package_id,
            "status": "completed",
            "zip_path": zip_path,
            "sha256": zip_sha256,
        }

    def get_package(self, task_id: str) -> OutputPackageRecord:
        record = (
            self.db.query(OutputPackageRecord)
            .filter(OutputPackageRecord.task_id == task_id)
            .order_by(OutputPackageRecord.created_at.desc())
            .first()
        )
        if record is None:
            raise LookupError("package not found")
        return record

    def get_download_path(self, task_id: str) -> Path:
        record = self.get_package(task_id)
        return self.storage.resolve(record.zip_path)

    def _get_task(self, task_id: str) -> ConversionTask:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")
        return task

    def _generate_metadata(self, task: ConversionTask) -> None:
        metadata = {
            "package_version": "1.0.0",
            "task_id": task.task_id,
            "doc_id": task.doc_id,
            "schema_id": task.schema_id,
            "template_id": task.template_id,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.storage.save_json(f"tasks/{task.task_id}/metadata.json", metadata)

    def _generate_config_snapshot(self, task: ConversionTask) -> None:
        snapshot = {
            "input_hash": task.input_hash,
            "schema_id": task.schema_id,
            "schema_version": task.schema_version,
            "template_id": task.template_id,
            "template_version": task.template_version,
            "options": json.loads(task.options_json or "{}"),
            "engine_version": "1.0.0",
            "llm_mode": "disabled",
            "llm_model": None,
            "prompt_version": None,
        }
        self.storage.save_json(f"tasks/{task.task_id}/config_snapshot.json", snapshot)

    def _ensure_mapping_report(self, task_id: str) -> None:
        path = f"tasks/{task_id}/mapping_report.json"
        try:
            self.storage.read_json(path)
        except FileNotFoundError:
            self.storage.save_json(path, {"task_id": task_id, "mappings": []})

    def _ensure_trace(self, task_id: str) -> None:
        trace_service = TraceService(self.db, self.storage)
        trace_service.export_trace_json(task_id)

    def _persist_validation_report(self, task_id: str, report) -> None:
        self.db.query(ValidationReportRecord).filter(
            ValidationReportRecord.task_id == task_id
        ).delete()
        self.db.add(ValidationReportRecord(
            report_id=new_id("vrep"),
            task_id=task_id,
            passed=report.passed,
            error_count=report.summary.get("error_count", 0),
            warning_count=report.summary.get("warning_count", 0),
            report_json=report.model_dump_json(),
        ))

    def _persist_consistency_report(self, task_id: str, report) -> None:
        self.db.query(ConsistencyReportRecord).filter(
            ConsistencyReportRecord.task_id == task_id
        ).delete()
        self.db.add(ConsistencyReportRecord(
            report_id=new_id("crep"),
            task_id=task_id,
            passed=report.passed,
            error_count=len(report.checks) - sum(1 for c in report.checks if c.passed),
            warning_count=0,
            report_json=report.model_dump_json(),
        ))
