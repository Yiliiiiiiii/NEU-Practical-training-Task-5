from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.config import Settings
from app.schemas.topic5_convert import Topic5ConvertRequest, Topic5ConvertResponse
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.services.conversion_status_service import ConversionStatusService
from app.services.package_service import PackageService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService
from app.services.topic5_conversion_engine import (
    ConversionEngineContext,
    Topic5ConversionEngine,
)
from app.utils.ids import new_id


class Topic5ConversionService:
    def __init__(
        self, storage_root: str | Path, *, settings: Settings | None = None
    ) -> None:
        self.storage_root = Path(storage_root)
        self.settings = settings or Settings()

    def convert(
        self,
        request: Topic5ConvertRequest,
        *,
        create_package: bool = False,
    ) -> Topic5ConvertResponse:
        task_id = new_id("topic5")
        doc_id = request.uir.doc_id or new_id("inline_doc")
        schema = SchemaService().validate_schema(request.target_schema)
        template = TemplateService().validate_template(
            request.effective_mapping_template,
            schema,
        )
        legacy_options = dict(request.options)
        legacy_options["enable_legacy_transform_heuristics"] = (
            request.enable_legacy_transform_heuristics
        )
        legacy_options.setdefault("enable_llm_fallback", False)
        legacy_options.setdefault("enable_lineage", False)
        legacy_options.setdefault(
            "no_code_schema_pack_onboarding", schema.schema_id == "announcement_doc"
        )
        execution_options, option_warnings = Topic5ExecutionOptions.parse_legacy(
            legacy_options
        )
        engine_result = Topic5ConversionEngine().convert(
            uir=request.uir,
            target_schema=schema,
            metadata_template=request.metadata_template,
            mapping_rules=template,
            content_organization=request.content_organization,
            execution_options=execution_options,
            output_assertions=request.output_assertions,
            engine_context=ConversionEngineContext(
                task_id=task_id,
                doc_id=doc_id,
                input_mode="inline_topic5_config",
                mapping_input_name=request.mapping_input_name,
                settings=self.settings,
                schema_pack_id=execution_options.schema_pack_id,
                schema_pack_version=execution_options.schema_pack_version,
                option_warnings=option_warnings,
            ),
        )

        manifest = None
        package_zip_path = None
        package_metadata = None
        verifier_report = None
        artifact_consistency_report = engine_result.artifact_consistency_report
        if create_package:
            package_result = PackageService(
                self.storage_root,
                max_zip_bytes=self.settings.topic5_max_zip_bytes,
            ).create_package(
                task_id=task_id,
                doc_id=doc_id,
                schema=schema,
                template=template,
                canonical=engine_result.canonical,
                rendered=engine_result.rendered,
                mapping_report=engine_result.mapping_report,
                transform_report=engine_result.transform_result.report,
                validation_report=engine_result.validation_report,
                content_organization_report=(
                    engine_result.content_organization_report
                ),
                conversion_assertion_report=(
                    engine_result.conversion_assertion_report
                ),
                include_assertion_report=(
                    execution_options.include_assertion_report_in_package
                ),
                metadata_result=engine_result.metadata_result,
                metadata_template=request.metadata_template,
                document_summary=engine_result.document_summary,
                artifact_consistency_report=artifact_consistency_report,
            )
            manifest = package_result.manifest.model_dump(mode="json")
            package_zip_path = package_result.metadata.zip_path
            package_metadata = package_result.metadata.model_dump(mode="json")
            verifier_report = package_result.verifier_report.model_dump(mode="json")
            artifact_consistency_report = package_result.artifact_consistency_report

        status_input = replace(
            engine_result.status_input,
            package_verifier_passed=(
                bool(verifier_report.get("passed"))
                if isinstance(verifier_report, dict)
                else None
            ),
            artifact_consistency_passed=artifact_consistency_report.passed,
        )
        status = ConversionStatusService.determine(status_input)
        summary_payload = (
            engine_result.document_summary.model_dump(mode="json")
            if engine_result.document_summary
            else None
        )
        metadata_result = engine_result.metadata_result
        return Topic5ConvertResponse(
            task_id=task_id,
            status=status,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            content_json=engine_result.rendered.structured_json,
            content_markdown=engine_result.rendered.markdown,
            chunks=engine_result.rendered.chunks,
            mapping_report=engine_result.mapping_report.model_dump(mode="json"),
            transform_report=engine_result.transform_result.report,
            validation_report=engine_result.validation_report.model_dump(mode="json"),
            content_organization_report=(
                engine_result.content_organization_report.model_dump(mode="json")
            ),
            mapping_repair_report=engine_result.mapping_repair_report,
            manifest=manifest,
            package_zip_path=package_zip_path,
            package_metadata=package_metadata,
            verifier_report=verifier_report,
            conversion_assertion_report=engine_result.conversion_assertion_report,
            document_metadata=(
                metadata_result.document_metadata if metadata_result else {}
            ),
            metadata_template_report=(
                metadata_result.report.model_dump(mode="json")
                if metadata_result
                else None
            ),
            document_summary=summary_payload,
            artifact_consistency_report=artifact_consistency_report.model_dump(
                mode="json"
            ),
            conversion_fingerprints=engine_result.conversion_fingerprints,
            semantic_artifact_hashes=engine_result.semantic_artifact_hashes,
            execution_option_warnings=option_warnings,
        )
