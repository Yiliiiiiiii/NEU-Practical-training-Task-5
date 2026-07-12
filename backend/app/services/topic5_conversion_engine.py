from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.schemas.canonical import CanonicalModel
from app.schemas.content_organization import (
    ContentOrganizationOptions,
    ContentOrganizationReport,
)
from app.schemas.conversion_assertions import ConversionAssertionConfig
from app.schemas.document_summary import DocumentSummary
from app.schemas.mapping_template import MappingTemplate
from app.schemas.metadata_template import MetadataRenderResult, MetadataTemplateConfig
from app.schemas.reports import MappingReport, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.schemas.uir import UIRDocument
from app.services.artifact_consistency_service import ArtifactConsistencyService
from app.services.candidate_service import CandidateService
from app.services.canonical_service import CanonicalService
from app.services.chunk_organizer_service import ChunkOrganizerService
from app.services.chunk_providers.resolver import ChunkProviderResolver
from app.services.conversion_assertion_service import ConversionAssertionService
from app.services.conversion_fingerprint_service import ConversionFingerprintService
from app.services.conversion_status_service import (
    ConversionStatusInput,
    ConversionStatusService,
)
from app.services.document_summary_service import DocumentSummaryService
from app.services.llm_fallback_service import LLMFallbackService
from app.services.mapping_repair_service import MappingRepairService
from app.services.mapping_service import MappingService
from app.services.metadata_template_service import MetadataTemplateService
from app.services.render_service import RenderedArtifacts, RenderService
from app.services.transform_service import TransformResult, TransformService
from app.services.validation_service import ValidationService


@dataclass(frozen=True)
class ConversionEngineContext:
    task_id: str
    doc_id: str
    input_mode: str
    mapping_input_name: str
    settings: Settings
    schema_pack_id: str | None = None
    schema_pack_version: str | None = None
    execution_snapshot_fields: dict[str, Any] = field(default_factory=dict)
    option_warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ConversionEngineResult:
    canonical: CanonicalModel
    rendered: RenderedArtifacts
    mapping_report: MappingReport
    mapping_repair_report: dict[str, Any] | None
    transform_result: TransformResult
    metadata_result: MetadataRenderResult | None
    validation_report: ValidationReport
    content_organization_report: ContentOrganizationReport
    document_summary: DocumentSummary | None
    artifact_consistency_report: Any
    conversion_assertion_report: dict[str, Any] | None
    provider_trace: dict[str, Any]
    status_input: ConversionStatusInput
    conversion_fingerprints: dict[str, str]
    semantic_artifact_hashes: dict[str, str]
    execution_snapshot: dict[str, Any]
    candidates: list[Any]


class Topic5ConversionEngine:
    def convert(
        self,
        *,
        uir: UIRDocument,
        target_schema: TargetSchema,
        metadata_template: MetadataTemplateConfig | None,
        mapping_rules: MappingTemplate,
        content_organization: ContentOrganizationOptions,
        execution_options: Topic5ExecutionOptions,
        output_assertions: ConversionAssertionConfig | None,
        engine_context: ConversionEngineContext,
    ) -> ConversionEngineResult:
        options = execution_options.runtime_dict()
        candidates = CandidateService().extract_candidates(
            engine_context.task_id,
            uir,
            candidate_profile=execution_options.candidate_profile,
            enable_legacy_domain_rules=(
                execution_options.enable_legacy_candidate_heuristics
            ),
        )
        mapping_report = MappingService(
            llm_fallback_service=LLMFallbackService(engine_context.settings)
        ).map_fields(
            task_id=engine_context.task_id,
            uir=uir,
            schema=target_schema,
            template=mapping_rules,
            candidates=candidates,
            options=options,
        )
        mapping_repair_report = None
        if execution_options.enable_mapping_repair:
            mapping_report, mapping_repair_report = MappingRepairService().repair(
                task_id=engine_context.task_id,
                uir=uir,
                schema=target_schema,
                template=mapping_rules,
                candidates=candidates,
                mapping_report=mapping_report,
                options=options,
            )
        mapping_report.summary.update(
            {
                "input_mode": engine_context.input_mode,
                "mapping_input_name": engine_context.mapping_input_name,
                "thresholds": execution_options.thresholds,
                "no_code_schema_pack_onboarding": (
                    execution_options.no_code_schema_pack_onboarding
                ),
                "execution_option_warnings": engine_context.option_warnings,
            }
        )

        transform_result = TransformService().transform(
            engine_context.task_id,
            uir,
            target_schema,
            mapping_rules,
            mapping_report,
            enable_legacy_transform_heuristics=(
                execution_options.enable_legacy_transform_heuristics
            ),
        )
        metadata_result = None
        if metadata_template is not None:
            metadata_result = MetadataTemplateService().render(
                uir=uir,
                transformed_fields=transform_result.data,
                template=metadata_template,
                system_context={
                    "doc_id": engine_context.doc_id,
                    "schema_id": target_schema.schema_id,
                    "schema_version": target_schema.version,
                    "template_id": mapping_rules.template_id,
                    "template_version": mapping_rules.version,
                    "metadata_template_id": metadata_template.template_id,
                    "metadata_template_version": metadata_template.version,
                },
            )

        execution_snapshot = {
            "task_id": engine_context.task_id,
            "doc_id": engine_context.doc_id,
            "schema_id": target_schema.schema_id,
            "schema_version": target_schema.version,
            "template_id": mapping_rules.template_id,
            "template_version": mapping_rules.version,
            "input_mode": engine_context.input_mode,
            "mapping_input_name": engine_context.mapping_input_name,
            "options": options,
            **engine_context.execution_snapshot_fields,
        }
        canonical = CanonicalService().build_canonical(
            task_id=engine_context.task_id,
            uir=uir,
            schema=target_schema,
            template=mapping_rules,
            transform_result=transform_result,
            mapping_report=mapping_report,
            execution_snapshot=execution_snapshot,
            metadata_result=metadata_result,
            metadata_template=metadata_template,
        )
        rendered = RenderService().render(
            canonical, chunk_size=execution_options.chunk_size
        )
        preliminary_validation = ValidationService().validate(
            engine_context.task_id,
            target_schema,
            rendered,
            metadata_issues=(metadata_result.report.issues if metadata_result else None),
        )
        provider_result = ChunkProviderResolver(
            settings=engine_context.settings
        ).resolve(
            canonical=canonical,
            options=content_organization,
            legacy_chunks=rendered.chunks,
        )
        organized_chunks, organization_report = ChunkOrganizerService().organize_chunks(
            chunks=provider_result.chunks,
            canonical_model=canonical,
            schema=target_schema,
            mapping_report=mapping_report,
            validation_report=preliminary_validation,
            task_id=engine_context.task_id,
            doc_id=engine_context.doc_id,
            schema_id=target_schema.schema_id,
            template_id=mapping_rules.template_id,
            template_version=mapping_rules.version,
            options=content_organization,
            use_provided_chunks=True,
        )
        organization_report.provider_trace = provider_result.trace.model_dump(mode="json")
        document_summary = DocumentSummaryService().build(
            canonical=canonical,
            chunks=organized_chunks,
            config=content_organization.summary,
        )
        document_summary_payload = (
            document_summary.model_dump(mode="json") if document_summary else None
        )
        canonical.doc_meta["document_summary"] = document_summary_payload
        organization_report.document_summary = document_summary_payload
        summary_rendered = RenderService().render(
            canonical, chunk_size=execution_options.chunk_size
        )
        rendered = RenderedArtifacts(
            structured_json=summary_rendered.structured_json,
            markdown=summary_rendered.markdown,
            chunks=organized_chunks,
        )
        validation_report = ValidationService().validate(
            engine_context.task_id,
            target_schema,
            rendered,
            require_content_organization=True,
            metadata_issues=(metadata_result.report.issues if metadata_result else None),
        )
        artifact_consistency_report = ArtifactConsistencyService().verify(
            canonical=canonical,
            structured_json=rendered.structured_json,
            markdown=rendered.markdown,
            chunks=rendered.chunks,
            document_summary=document_summary,
            block_exclusions=[
                item.model_dump(mode="json")
                for item in content_organization.block_exclusions
            ],
            block_exclusion_rule_ids={
                rule.rule_id for rule in content_organization.block_exclusion_rules
            },
            protect_tables=content_organization.protect_tables,
            protect_lists=content_organization.protect_lists,
            protect_code_blocks=content_organization.protect_code_blocks,
        )
        conversion_assertion_report = None
        if output_assertions is not None:
            assertion_report = ConversionAssertionService().evaluate(
                task_id=engine_context.task_id,
                schema_pack_id=(
                    engine_context.schema_pack_id or target_schema.schema_id
                ),
                schema_pack_version=(
                    engine_context.schema_pack_version or target_schema.version
                ),
                schema_id=target_schema.schema_id,
                content_json=rendered.structured_json,
                assertion_config=output_assertions,
                mapping_report=mapping_report.model_dump(mode="json"),
            )
            conversion_assertion_report = assertion_report.model_dump(mode="json")

        status_input = ConversionStatusInput(
            mapping_review_item_count=len(mapping_report.review_required_items),
            unmapped_required_source_present_count=(
                ConversionStatusService.count_required_unmapped_source_present(
                    mapping_report.unmapped
                )
            ),
            schema_validation_passed=validation_report.passed,
            assertion_error_count=(
                int(conversion_assertion_report.get("error_count", 0))
                if conversion_assertion_report
                else 0
            ),
            strict_output_assertions=execution_options.strict_output_assertions,
            metadata_passed=(metadata_result.passed if metadata_result else None),
            strict_metadata=execution_options.strict_metadata_template,
            summary_faithfulness_passed=(
                document_summary.faithfulness_passed if document_summary else None
            ),
            artifact_consistency_passed=artifact_consistency_report.passed,
            provider_fallback_used=provider_result.trace.fallback_used,
            provider_fallback_requires_review=(
                execution_options.provider_fallback_requires_review
            ),
        )
        conversion_fingerprints = ConversionFingerprintService.conversion_fingerprints(
            uir=uir,
            target_schema=target_schema,
            metadata_template=metadata_template,
            mapping_rules=mapping_rules,
            content_organization=content_organization,
            execution_options=execution_options,
        )
        semantic_artifact_hashes = (
            ConversionFingerprintService.semantic_artifact_hashes(
                data=rendered.structured_json.get("data", {}),
                document_metadata=rendered.structured_json.get(
                    "document_metadata", {}
                ),
                document_summary=document_summary_payload,
                canonical_blocks=canonical.blocks,
                chunks=rendered.chunks,
                tag_traces=[
                    chunk.get("organization_trace", {})
                    for chunk in rendered.chunks
                ],
                entity_tags=[
                    chunk.get("entity_tags", []) for chunk in rendered.chunks
                ],
                reports={
                    "mapping": mapping_report.model_dump(mode="json"),
                    "transform": transform_result.report,
                    "validation": validation_report.model_dump(mode="json"),
                    "content_organization": organization_report.model_dump(
                        mode="json"
                    ),
                    "artifact_consistency": (
                        artifact_consistency_report.model_dump(mode="json")
                    ),
                },
            )
        )
        return ConversionEngineResult(
            canonical=canonical,
            rendered=rendered,
            mapping_report=mapping_report,
            mapping_repair_report=mapping_repair_report,
            transform_result=transform_result,
            metadata_result=metadata_result,
            validation_report=validation_report,
            content_organization_report=organization_report,
            document_summary=document_summary,
            artifact_consistency_report=artifact_consistency_report,
            conversion_assertion_report=conversion_assertion_report,
            provider_trace=provider_result.trace.model_dump(mode="json"),
            status_input=status_input,
            conversion_fingerprints=conversion_fingerprints,
            semantic_artifact_hashes=semantic_artifact_hashes,
            execution_snapshot=execution_snapshot,
            candidates=candidates,
        )
