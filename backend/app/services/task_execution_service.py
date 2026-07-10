import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ConversionTask, Document, KnowledgeCandidateRecord
from app.schemas.conversion_assertions import ConversionAssertionConfig
from app.schemas.mapping_template import MappingTemplate
from app.schemas.metadata_template import MetadataRenderResult, MetadataTemplateConfig
from app.schemas.reports import MappingReport
from app.schemas.schema_pack_contract import SchemaPackManifest
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.canonical_service import CanonicalService
from app.services.catalog_governance_service import CatalogGovernanceService
from app.services.chunk_organizer_service import ChunkOrganizerService
from app.services.conversion_assertion_service import ConversionAssertionService
from app.services.effective_template_service import EffectiveTemplateService
from app.services.lineage_graph_service import LineageGraphService
from app.services.llm_fallback_service import LLMFallbackService
from app.services.mapping_service import MappingService
from app.services.metadata_template_service import MetadataTemplateService
from app.services.package_service import PackageService
from app.services.render_service import RenderedArtifacts, RenderService
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService
from app.services.schema_pack_service import SchemaPackService
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
        "manifest": "manifest",
        "lineage": "lineage_graph",
        "lineage_graph": "lineage_graph",
        "lineage-summary": "lineage_summary",
        "lineage_summary": "lineage_summary",
        "assertions": "conversion_assertion_report",
        "conversion-assertions": "conversion_assertion_report",
        "conversion_assertion_report": "conversion_assertion_report",
        "metadata-template": "metadata_template_report",
        "metadata_template": "metadata_template_report",
        "metadata_template_report": "metadata_template_report",
    }

    def __init__(
        self,
        db: Session,
        storage: StorageService,
        schema_service: SchemaService | None = None,
        template_service: TemplateService | None = None,
        settings: Settings | None = None,
        schema_pack_service: SchemaPackService | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.schema_service = schema_service or SchemaService()
        self.template_service = template_service or TemplateService()
        self.settings = settings or Settings()
        self.schema_pack_service = schema_pack_service or SchemaPackService()

    def execute_task(self, task_id: str) -> TaskExecutionResult:
        task = self.db.get(ConversionTask, task_id)
        if task is None:
            raise LookupError("task not found")

        started_at = self._now()
        claimed = (
            self.db.query(ConversionTask)
            .filter(
                ConversionTask.task_id == task_id,
                ConversionTask.status == "created",
            )
            .update(
                {
                    ConversionTask.started_at: started_at,
                    ConversionTask.finished_at: None,
                    ConversionTask.updated_at: started_at,
                    ConversionTask.status: "running",
                    ConversionTask.error_code: None,
                    ConversionTask.error_message: None,
                },
                synchronize_session=False,
            )
        )
        if claimed != 1:
            self.db.rollback()
            raise ValueError(
                "task has already been executed; create a new task to rerun"
            )
        self.db.commit()
        self.db.refresh(task)

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
        schema_pack_id = options.get("schema_pack_id")
        assertion_config = None
        schema_pack_manifest = None
        if isinstance(schema_pack_id, str) and schema_pack_id:
            (
                schema,
                template,
                assertion_config,
                schema_pack_manifest,
            ) = self._load_schema_pack_contract(
                task,
                schema_pack_id,
                options,
                input_uir_version=uir.uir_version,
            )
        else:
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
        metadata_template_payload = options.get("metadata_template")
        metadata_template = (
            MetadataTemplateConfig.model_validate(metadata_template_payload)
            if isinstance(metadata_template_payload, dict)
            else None
        )
        if (
            metadata_template is not None
            and metadata_template.schema_id != schema.schema_id
        ):
            raise ValueError("metadata template schema_id does not match target schema")
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

        candidates = CandidateService().extract_candidates(
            task.task_id,
            uir,
            candidate_profile=options.get("candidate_profile"),
            enable_legacy_domain_rules=not bool(schema_pack_manifest),
        )
        llm_fallback_service = LLMFallbackService(self.settings)
        mapping_report = MappingService(llm_fallback_service=llm_fallback_service).map_fields(
            task_id=task.task_id,
            uir=uir,
            schema=schema,
            template=template,
            candidates=candidates,
            options=options,
        )
        review_records = review_knowledge_service.create_pending_reviews(
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
        metadata_result = None
        if metadata_template is not None:
            metadata_result = MetadataTemplateService().render(
                uir=uir,
                transformed_fields=transform_result.data,
                template=metadata_template,
                system_context={
                    "doc_id": document.doc_id,
                    "schema_id": schema.schema_id,
                    "schema_version": schema.version,
                    "template_id": template.template_id,
                    "template_version": template.version,
                    "metadata_template_id": metadata_template.template_id,
                    "metadata_template_version": metadata_template.version,
                },
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
            "llm": {
                **llm_fallback_service.safe_config_snapshot(
                    strict_failure=bool(
                        options.get("strict_llm", self.settings.llm_strict_failure)
                    )
                ),
                "task_requested": bool(options.get("enable_llm_fallback", False)),
            },
            "started_at": started_at,
        }
        snapshot_path = f"tasks/{task.task_id}/execution_snapshot.json"
        canonical = CanonicalService().build_canonical(
            task_id=task.task_id,
            uir=uir,
            schema=schema,
            template=template,
            transform_result=transform_result,
            mapping_report=mapping_report,
            execution_snapshot=execution_snapshot,
            metadata_result=metadata_result,
            metadata_template=metadata_template,
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
            options=options.get("content_organization"),
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
            metadata_issues=(metadata_result.report.issues if metadata_result else None),
        )
        conversion_assertion_report: dict[str, Any] | None = None
        conversion_assertion_report_path: str | None = None
        if assertion_config is not None and schema_pack_manifest is not None:
            assertion_report = ConversionAssertionService().evaluate(
                task_id=task.task_id,
                schema_pack_id=schema_pack_manifest.schema_pack_id,
                schema_pack_version=schema_pack_manifest.schema_pack_version,
                schema_id=schema.schema_id,
                content_json=rendered.structured_json,
                assertion_config=assertion_config,
                mapping_report=mapping_report.model_dump(mode="json"),
            )
            conversion_assertion_report = assertion_report.model_dump(mode="json")
            conversion_assertion_report_path = str(
                self.storage.save_json(
                    f"tasks/{task.task_id}/conversion_assertion_report.json",
                    conversion_assertion_report,
                )
            )
            execution_snapshot.update(
                {
                    "status": "running",
                    "artifacts": {
                        "conversion_assertion_report": (
                            conversion_assertion_report_path
                        )
                    },
                    "report_paths": {
                        "conversion_assertion_report": (
                            conversion_assertion_report_path
                        )
                    },
                }
            )
            self.storage.save_json(snapshot_path, execution_snapshot)
            task.config_snapshot_path = snapshot_path
            task.updated_at = self._now()
            self.db.commit()
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
            conversion_assertion_report=conversion_assertion_report,
            include_assertion_report=bool(
                options.get("include_assertion_report_in_package", False)
            ),
            metadata_result=metadata_result,
            metadata_template=metadata_template,
        )

        lineage_graph: dict[str, Any] | None = None
        lineage_summary: dict[str, Any] | None = None
        lineage_warnings: list[str] = []
        if bool(options.get("enable_lineage", True)):
            external_options = options.get("external_uir")
            adapter_report = (
                external_options.get("adapter_report")
                if isinstance(external_options, dict)
                else None
            )
            knowledge_records: list[dict[str, Any]] = [
                {
                    "record_type": "pack",
                    "pack_id": pack.pack_id,
                    "schema_id": pack.schema_id,
                    "template_id": pack.template_id,
                    "status": pack.status,
                    "candidate_ids": pack.candidate_ids,
                }
                for pack in active_packs
            ]
            review_ids = [record.review_id for record in review_records]
            if review_ids:
                knowledge_records.extend(
                    {
                        "record_type": "candidate",
                        "candidate_id": record.candidate_id,
                        "review_id": record.review_id,
                        "target_field_id": record.target_field_id,
                        "alias": record.alias,
                        "candidate_type": record.candidate_type,
                        "badcase_hit": record.badcase_hit,
                        "status": record.status,
                    }
                    for record in self.db.scalars(
                        select(KnowledgeCandidateRecord).where(
                            KnowledgeCandidateRecord.review_id.in_(review_ids)
                        )
                    )
                )
            try:
                graph = LineageGraphService().build(
                    task_id=task.task_id,
                    doc_id=document.doc_id,
                    uir=uir,
                    candidates=candidates,
                    mapping_report=mapping_report,
                    schema=schema,
                    template=template,
                    canonical=canonical,
                    chunks=rendered.chunks,
                    manifest=package_result.manifest,
                    adapter_report=adapter_report,
                    review_decisions=[
                        {
                            "review_id": record.review_id,
                            "mapping_id": record.mapping_id,
                            "candidate_id": record.candidate_id,
                            "target_field_id": record.target_field_id,
                            "status": record.status,
                            "decision": record.decision,
                            "reason": record.reason,
                            "review_comment": record.review_comment,
                            "reviewer": record.reviewer,
                            "confidence": record.confidence,
                        }
                        for record in review_records
                    ],
                    knowledge_records=knowledge_records,
                    applied_knowledge_pack_ids=effective_result.applied_pack_ids,
                )
                lineage_graph = graph.model_dump(mode="json")
                lineage_summary = graph.summary
            except Exception as exc:
                if bool(options.get("strict_lineage", False)):
                    raise
                lineage_warnings.append(str(exc))

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
            manifest=package_result.manifest.model_dump(mode="json"),
            conversion_assertion_report_path=conversion_assertion_report_path,
            lineage_graph=lineage_graph,
            lineage_summary=lineage_summary,
            metadata_result=metadata_result,
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
            assertion_error_count=(
                int(conversion_assertion_report.get("error_count", 0))
                if conversion_assertion_report
                else 0
            ),
            strict_output_assertions=bool(
                options.get("strict_output_assertions", False)
            ),
            metadata_passed=(metadata_result.passed if metadata_result else None),
            strict_metadata_template=bool(
                options.get("strict_metadata_template", False)
            ),
        )
        artifacts: dict[str, str] = {}
        assertion_report_path = report_paths.get("conversion_assertion_report")
        if assertion_report_path is not None:
            artifacts["conversion_assertion_report"] = assertion_report_path
        execution_snapshot.update(
            {
                "status": status,
                "finished_at": finished_at.isoformat(),
                "artifacts": artifacts,
                "report_paths": report_paths,
                "package_zip_path": package_result.metadata.zip_path,
                "review_required_count": review_required_count,
                "unmapped_required_count": unmapped_required_count,
                "validation_passed": validation_report.passed,
                "package_verifier_passed": package_result.verifier_report.passed,
                "metadata_template_passed": (
                    metadata_result.passed if metadata_result else None
                ),
                "lineage_warnings": lineage_warnings,
            }
        )
        self.storage.save_json(snapshot_path, execution_snapshot)

        task.status = status
        task.config_snapshot_path = snapshot_path
        task.finished_at = finished_at
        task.updated_at = finished_at
        if status != "failed":
            task.error_code = None
            task.error_message = None
        elif not package_result.verifier_report.passed:
            task.error_code = "package_verification_failed"
            task.error_message = "package verification failed"
        else:
            task.error_code = "output_assertion_failed"
            task.error_message = "strict output assertion failed"
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

    def _load_schema_pack_contract(
        self,
        task: ConversionTask,
        schema_pack_id: str,
        options: dict[str, Any],
        *,
        input_uir_version: str,
    ) -> tuple[
        TargetSchema,
        MappingTemplate,
        ConversionAssertionConfig | None,
        SchemaPackManifest,
    ]:
        manifest = self.schema_pack_service.validate_for_execution(
            schema_pack_id,
            input_uir_version=input_uir_version,
        )
        if manifest.schema_pack_id != task.schema_id:
            raise ValueError("schema_pack_id does not match task.schema_id")

        schema = TargetSchema.model_validate(
            self.schema_pack_service.load_target_schema(schema_pack_id)
        )
        if schema.version != task.schema_version:
            raise ValueError("SchemaPack target schema version does not match task")

        mapping_payload = self.schema_pack_service.load_mapping_rules(schema_pack_id)
        regex_rules = [
            {
                key: item[key]
                for key in ("target_field_id", "pattern", "group")
                if key in item
            }
            for item in mapping_payload.get("regex_rules", [])
            if isinstance(item, dict)
        ]
        template = MappingTemplate.model_validate(
            {
                "template_id": mapping_payload.get("template_id"),
                "schema_id": mapping_payload.get("schema_id"),
                "name": mapping_payload.get("name") or manifest.display_name,
                "version": mapping_payload.get("version"),
                "aliases": mapping_payload.get("aliases", {}),
                "regex_rules": regex_rules,
                "transform_rules": mapping_payload.get("transform_rules", []),
                "defaults": mapping_payload.get("defaults", {}),
                "enum_maps": mapping_payload.get("enum_maps", {}),
            }
        )
        if template.template_id != task.template_id:
            raise ValueError("SchemaPack mapping template does not match task.template_id")
        if template.version != task.template_version:
            raise ValueError("SchemaPack mapping template version does not match task")

        options.setdefault("mapping_mode", manifest.execution.default_mapping_mode)
        options.setdefault("enable_llm_fallback", manifest.execution.allow_llm_fallback)
        options.setdefault(
            "include_assertion_report_in_package",
            manifest.execution.include_assertion_report_in_package,
        )
        options.setdefault(
            "content_organization",
            self.schema_pack_service.load_content_org(schema_pack_id),
        )
        options.setdefault(
            "metadata_template",
            self.schema_pack_service.load_metadata_template(schema_pack_id),
        )
        options.setdefault("negative_pairs", mapping_payload.get("negative_pairs", []))
        options.setdefault("thresholds", mapping_payload.get("thresholds", {}))
        options.setdefault("candidate_profile", mapping_payload.get("candidate_hints", {}))
        options["schema_pack_id"] = manifest.schema_pack_id
        options["schema_pack_version"] = manifest.schema_pack_version
        options["no_code_schema_pack_onboarding"] = True
        assertions = self.schema_pack_service.load_output_assertions(schema_pack_id)
        return schema, template, assertions, manifest

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
        manifest: dict[str, Any],
        conversion_assertion_report_path: str | None = None,
        lineage_graph: dict[str, Any] | None = None,
        lineage_summary: dict[str, Any] | None = None,
        metadata_result: MetadataRenderResult | None = None,
    ) -> dict[str, str]:
        base = f"tasks/{task_id}"
        report_paths = {
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
            "manifest": str(self.storage.save_json(f"{base}/manifest.json", manifest)),
        }
        if lineage_graph is not None:
            report_paths["lineage_graph"] = str(
                self.storage.save_json(
                    f"{base}/lineage_graph.json",
                    lineage_graph,
                )
            )
        if lineage_summary is not None:
            report_paths["lineage_summary"] = str(
                self.storage.save_json(
                    f"{base}/lineage_summary.json",
                    lineage_summary,
                )
            )
        if conversion_assertion_report_path is not None:
            report_paths["conversion_assertion_report"] = (
                conversion_assertion_report_path
            )
        if metadata_result is not None:
            report_paths["metadata_template_report"] = str(
                self.storage.save_json(
                    f"{base}/metadata_template_report.json",
                    metadata_result.report.model_dump(mode="json"),
                )
            )
        return report_paths

    @staticmethod
    def _final_status(
        package_passed: bool,
        review_required_count: int,
        unmapped_required_count: int,
        assertion_error_count: int = 0,
        strict_output_assertions: bool = False,
        metadata_passed: bool | None = None,
        strict_metadata_template: bool = False,
    ) -> str:
        if not package_passed:
            return "failed"
        if strict_output_assertions and assertion_error_count:
            return "failed"
        if strict_metadata_template and metadata_passed is False:
            return "failed"
        if (
            review_required_count
            or unmapped_required_count
            or assertion_error_count
            or metadata_passed is False
        ):
            return "review_required"
        return "completed"

    def _mark_failed(self, task: ConversionTask, error_code: str, message: str) -> None:
        now = self._now()
        if task.config_snapshot_path:
            try:
                snapshot = self.execution_snapshot(task)
                snapshot.update(
                    {
                        "status": "failed",
                        "finished_at": now.isoformat(),
                        "error_code": error_code,
                        "error_message": message,
                    }
                )
                self.storage.save_json(task.config_snapshot_path, snapshot)
            except (OSError, TypeError, ValueError):
                pass
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
