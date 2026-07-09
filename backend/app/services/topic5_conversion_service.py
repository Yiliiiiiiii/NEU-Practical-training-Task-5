from pathlib import Path
from typing import Any

from app.schemas.reports import MappingReport
from app.schemas.topic5_convert import Topic5ConvertRequest, Topic5ConvertResponse
from app.services.candidate_service import CandidateService
from app.services.canonical_service import CanonicalService
from app.services.chunk_organizer_service import ChunkOrganizerService
from app.services.mapping_service import MappingService
from app.services.package_service import PackageService
from app.services.render_service import RenderedArtifacts, RenderService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService
from app.services.transform_service import TransformService
from app.services.validation_service import ValidationService
from app.utils.ids import new_id


class Topic5ConversionService:
    def __init__(self, storage_root: str | Path) -> None:
        self.storage_root = Path(storage_root)

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
        content_organization = request.content_organization.model_dump(mode="json")

        options: dict[str, Any] = dict(request.options)
        options.setdefault("enable_llm_fallback", False)
        options.setdefault("enable_lineage", False)
        options.setdefault("topic5_inline_config", True)
        options["content_organization"] = content_organization
        options.setdefault("no_code_schema_pack_onboarding", schema.schema_id == "announcement_doc")
        if request.metadata_template is not None:
            options["metadata_template"] = request.metadata_template.model_dump(mode="json")

        candidates = CandidateService().extract_candidates(
            task_id,
            request.uir,
            candidate_profile=options.get("candidate_profile"),
            enable_legacy_domain_rules=False,
        )
        mapping_report = MappingService().map_fields(
            task_id=task_id,
            uir=request.uir,
            schema=schema,
            template=template,
            candidates=candidates,
            options=options,
        )
        mapping_report.summary["input_mode"] = "inline_topic5_config"
        mapping_report.summary["mapping_input_name"] = request.mapping_input_name
        mapping_report.summary["thresholds"] = options.get("thresholds", {})
        mapping_report.summary["no_code_schema_pack_onboarding"] = bool(
            options.get("no_code_schema_pack_onboarding")
        )

        transform_result = TransformService().transform(
            task_id,
            request.uir,
            schema,
            template,
            mapping_report,
        )
        execution_snapshot = {
            "task_id": task_id,
            "doc_id": doc_id,
            "schema_id": schema.schema_id,
            "schema_version": schema.version,
            "template_id": template.template_id,
            "template_version": template.version,
            "input_mode": "inline_topic5_config",
            "mapping_input_name": request.mapping_input_name,
            "options": options,
        }
        canonical = CanonicalService().build_canonical(
            task_id=task_id,
            uir=request.uir,
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
        preliminary_validation = ValidationService().validate(task_id, schema, rendered)
        organized_chunks, content_organization_report = ChunkOrganizerService().organize_chunks(
            chunks=rendered.chunks,
            canonical_model=canonical,
            schema=schema,
            mapping_report=mapping_report,
            validation_report=preliminary_validation,
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            template_version=template.version,
            options=content_organization,
        )
        rendered = RenderedArtifacts(
            structured_json=rendered.structured_json,
            markdown=rendered.markdown,
            chunks=organized_chunks,
        )
        validation_report = ValidationService().validate(
            task_id,
            schema,
            rendered,
            require_content_organization=True,
        )

        manifest = None
        package_zip_path = None
        package_metadata = None
        verifier_report = None
        if create_package:
            package_result = PackageService(self.storage_root).create_package(
                task_id=task_id,
                doc_id=doc_id,
                schema=schema,
                template=template,
                canonical=canonical,
                rendered=rendered,
                mapping_report=mapping_report,
                transform_report=transform_result.report,
                validation_report=validation_report,
                content_organization_report=content_organization_report,
            )
            manifest = package_result.manifest.model_dump(mode="json")
            package_zip_path = package_result.metadata.zip_path
            package_metadata = package_result.metadata.model_dump(mode="json")
            verifier_report = package_result.verifier_report.model_dump(mode="json")

        verifier_passed = (
            bool(verifier_report.get("passed"))
            if isinstance(verifier_report, dict)
            else None
        )
        status = self._final_status(
            mapping_report=mapping_report,
            validation_passed=validation_report.passed,
            verifier_passed=verifier_passed,
            create_package=create_package,
        )
        return Topic5ConvertResponse(
            task_id=task_id,
            status=status,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            content_json=rendered.structured_json,
            content_markdown=rendered.markdown,
            chunks=rendered.chunks,
            mapping_report=mapping_report.model_dump(mode="json"),
            transform_report=transform_result.report,
            validation_report=validation_report.model_dump(mode="json"),
            content_organization_report=content_organization_report.model_dump(mode="json"),
            manifest=manifest,
            package_zip_path=package_zip_path,
            package_metadata=package_metadata,
            verifier_report=verifier_report,
        )

    @staticmethod
    def _final_status(
        *,
        mapping_report: MappingReport,
        validation_passed: bool,
        verifier_passed: bool | None,
        create_package: bool,
    ) -> str:
        review_required_count = len(mapping_report.review_required_items)
        unmapped_required_count = sum(
            1 for item in mapping_report.unmapped if item.get("required")
        )

        if create_package and verifier_passed is False:
            return "failed"

        if review_required_count or unmapped_required_count or not validation_passed:
            return "review_required"

        return "completed"
