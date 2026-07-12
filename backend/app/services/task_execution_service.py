import json
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import ConversionTask, Document, KnowledgeCandidateRecord
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.conversion_assertions import ConversionAssertionConfig
from app.schemas.mapping_template import MappingTemplate
from app.schemas.metadata_template import MetadataRenderResult, MetadataTemplateConfig
from app.schemas.reports import MappingReport
from app.schemas.schema_pack_contract import SchemaPackManifest
from app.schemas.target_schema import TargetSchema
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.schemas.uir import UIRDocument
from app.services.catalog_governance_service import CatalogGovernanceService
from app.services.conversion_status_service import (
    ConversionStatusService,
)
from app.services.effective_template_service import EffectiveTemplateService
from app.services.lineage_graph_service import LineageGraphService
from app.services.llm_fallback_service import LLMFallbackService
from app.services.package_service import PackageService
from app.services.review_knowledge_workflow_service import ReviewKnowledgeWorkflowService
from app.services.schema_pack_service import SchemaPackService
from app.services.schema_service import SchemaService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService
from app.services.template_service import TemplateService
from app.services.topic5_conversion_engine import (
    ConversionEngineContext,
    Topic5ConversionEngine,
)


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
        "artifact-consistency": "artifact_consistency_report",
        "artifact_consistency": "artifact_consistency_report",
        "artifact_consistency_report": "artifact_consistency_report",
        "fingerprints": "fingerprints",
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
            raise ValueError("task has already been executed; create a new task to rerun")
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
        if metadata_template is not None and metadata_template.schema_id != schema.schema_id:
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

        llm_fallback_service = LLMFallbackService(self.settings)
        started_at = (task.started_at or self._now()).isoformat()
        content_org_payload = options.get("content_organization")
        content_org_options = (
            ContentOrganizationOptions.model_validate(content_org_payload)
            if isinstance(content_org_payload, dict)
            else ContentOrganizationOptions()
        )
        engine_option_payload = {
            key: value
            for key, value in options.items()
            if key not in {"content_organization", "metadata_template"}
        }
        engine_option_payload.setdefault("enable_lineage", True)
        engine_option_payload.setdefault(
            "enable_legacy_candidate_heuristics", not bool(schema_pack_manifest)
        )
        execution_options, option_warnings = Topic5ExecutionOptions.parse_legacy(
            engine_option_payload
        )
        engine_result = Topic5ConversionEngine().convert(
            uir=uir,
            target_schema=schema,
            metadata_template=metadata_template,
            mapping_rules=template,
            content_organization=content_org_options,
            execution_options=execution_options,
            output_assertions=assertion_config,
            engine_context=ConversionEngineContext(
                task_id=task.task_id,
                doc_id=document.doc_id,
                input_mode="registered_task",
                mapping_input_name="mapping_rules",
                settings=self.settings,
                schema_pack_id=(
                    schema_pack_manifest.schema_pack_id
                    if schema_pack_manifest is not None
                    else schema.schema_id
                ),
                schema_pack_version=(
                    schema_pack_manifest.schema_pack_version
                    if schema_pack_manifest is not None
                    else schema.version
                ),
                execution_snapshot_fields={
                    "applied_knowledge_pack_ids": effective_result.applied_pack_ids,
                    "input_hash": task.input_hash,
                    "llm": {
                        **llm_fallback_service.safe_config_snapshot(
                            strict_failure=execution_options.strict_llm
                        ),
                        "task_requested": execution_options.enable_llm_fallback,
                    },
                    "started_at": started_at,
                },
                option_warnings=option_warnings,
            ),
        )
        candidates = engine_result.candidates
        mapping_report = engine_result.mapping_report
        review_records = review_knowledge_service.create_pending_reviews(
            task=task,
            doc_id=document.doc_id,
            mapping_report=mapping_report,
        )
        transform_result = engine_result.transform_result
        metadata_result = engine_result.metadata_result
        execution_snapshot = engine_result.execution_snapshot
        snapshot_path = f"tasks/{task.task_id}/execution_snapshot.json"
        canonical = engine_result.canonical
        rendered = engine_result.rendered
        validation_report = engine_result.validation_report
        content_organization_report = engine_result.content_organization_report
        document_summary = engine_result.document_summary
        artifact_consistency_report = engine_result.artifact_consistency_report
        conversion_assertion_report = engine_result.conversion_assertion_report
        conversion_assertion_report_path: str | None = None
        if conversion_assertion_report is not None:
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
                        "conversion_assertion_report": (conversion_assertion_report_path)
                    },
                    "report_paths": {
                        "conversion_assertion_report": (conversion_assertion_report_path)
                    },
                }
            )
            self.storage.save_json(snapshot_path, execution_snapshot)
            task.config_snapshot_path = snapshot_path
            task.updated_at = self._now()
            self.db.commit()
        package_result = PackageService(
            self.storage.root,
            max_zip_bytes=self.settings.topic5_max_zip_bytes,
        ).create_package(
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
            include_assertion_report=(
                execution_options.include_assertion_report_in_package
            ),
            metadata_result=metadata_result,
            metadata_template=metadata_template,
            document_summary=document_summary,
            artifact_consistency_report=artifact_consistency_report,
        )

        lineage_graph: dict[str, Any] | None = None
        lineage_summary: dict[str, Any] | None = None
        lineage_warnings: list[str] = []
        if execution_options.enable_lineage:
            external_options = execution_options.external_uir
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
                if execution_options.strict_lineage:
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
            artifact_consistency_report=artifact_consistency_report.model_dump(mode="json"),
            fingerprints={
                "conversion": engine_result.conversion_fingerprints,
                "semantic_artifacts": engine_result.semantic_artifact_hashes,
            },
        )
        finished_at = self._now()
        review_required_count = len(mapping_report.review_required_items)
        unmapped_required_count = sum(1 for item in mapping_report.unmapped if item.get("required"))
        status = ConversionStatusService.determine(
            replace(
                engine_result.status_input,
                package_verifier_passed=package_result.verifier_report.passed,
                artifact_consistency_passed=artifact_consistency_report.passed,
            )
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
                "metadata_template_passed": (metadata_result.passed if metadata_result else None),
                "document_summary_faithfulness_passed": (
                    document_summary.faithfulness_passed if document_summary else None
                ),
                "artifact_consistency_passed": artifact_consistency_report.passed,
                "lineage_warnings": lineage_warnings,
                "conversion_fingerprints": engine_result.conversion_fingerprints,
                "semantic_artifact_hashes": (
                    engine_result.semantic_artifact_hashes
                ),
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
            {key: item[key] for key in ("target_field_id", "pattern", "group") if key in item}
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
                "scoring": mapping_payload.get("scoring", {}),
                "evidence_weights": mapping_payload.get("evidence_weights", {}),
                "unknown_evidence_policy": mapping_payload.get(
                    "unknown_evidence_policy", "neutral"
                ),
                "neutral_evidence_weight": mapping_payload.get("neutral_evidence_weight", 0.7),
                "constraints": mapping_payload.get("constraints", {}),
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
        options.setdefault("calibration", mapping_payload.get("calibration"))
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
        artifact_consistency_report: dict[str, Any] | None = None,
        fingerprints: dict[str, Any] | None = None,
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
            report_paths["conversion_assertion_report"] = conversion_assertion_report_path
        if metadata_result is not None:
            report_paths["metadata_template_report"] = str(
                self.storage.save_json(
                    f"{base}/metadata_template_report.json",
                    metadata_result.report.model_dump(mode="json"),
                )
            )
        if artifact_consistency_report is not None:
            report_paths["artifact_consistency_report"] = str(
                self.storage.save_json(
                    f"{base}/artifact_consistency_report.json",
                    artifact_consistency_report,
                )
            )
        if fingerprints is not None:
            report_paths["fingerprints"] = str(
                self.storage.save_json(
                    f"{base}/fingerprints.json",
                    fingerprints,
                )
            )
        return report_paths

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
