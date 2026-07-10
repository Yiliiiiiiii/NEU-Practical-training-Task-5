import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.schemas.artifact_consistency import ArtifactConsistencyReport
from app.schemas.canonical import CanonicalModel
from app.schemas.content_organization import ContentOrganizationReport
from app.schemas.document_summary import DocumentSummary
from app.schemas.mapping_template import MappingTemplate
from app.schemas.metadata_template import MetadataRenderResult, MetadataTemplateConfig
from app.schemas.package import Manifest, OutputPackageMetadata
from app.schemas.reports import ConsistencyReport, MappingReport, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.services.manifest_service import ManifestService
from app.services.package_verifier_service import PackageVerifierService
from app.services.render_service import RenderedArtifacts


@dataclass(frozen=True)
class PackageResult:
    metadata: OutputPackageMetadata
    verifier_report: ConsistencyReport
    manifest: Manifest


class PackageService:
    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def create_package(
        self,
        task_id: str,
        doc_id: str,
        schema: TargetSchema,
        template: MappingTemplate,
        canonical: CanonicalModel,
        rendered: RenderedArtifacts,
        mapping_report: MappingReport,
        transform_report: dict,
        validation_report: ValidationReport,
        content_organization_report: ContentOrganizationReport,
        conversion_assertion_report: dict | None = None,
        include_assertion_report: bool = False,
        metadata_result: MetadataRenderResult | None = None,
        metadata_template: MetadataTemplateConfig | None = None,
        document_summary: DocumentSummary | None = None,
        artifact_consistency_report: ArtifactConsistencyReport | None = None,
    ) -> PackageResult:
        package_id = f"pkg_{task_id}"
        package_dir = self.output_root / "packages" / package_id
        package_dir.mkdir(parents=True, exist_ok=True)

        document_metadata = (
            metadata_result.model_dump(mode="json")["document_metadata"]
            if metadata_result is not None
            else {}
        )
        metadata_template_ref = (
            {
                "template_id": metadata_template.template_id,
                "schema_id": metadata_template.schema_id,
                "version": metadata_template.version,
            }
            if metadata_template is not None
            else None
        )
        features = ["metadata_template_v1"] if metadata_result is not None else []
        if document_summary is not None:
            features.append("document_summary_v1")
        if artifact_consistency_report is not None:
            features.append("artifact_consistency_v1")

        files = {
            "content.json": rendered.structured_json,
            "mapping_report.json": mapping_report.model_dump(mode="json"),
            "transform_report.json": transform_report,
            "validation_report.json": validation_report.model_dump(mode="json"),
            "content_organization_report.json": content_organization_report.model_dump(mode="json"),
            "canonical.json": canonical.model_dump(mode="json"),
            "metadata.json": {
                "package_id": package_id,
                "package_version": "1.0.0",
                "task_id": task_id,
                "doc_id": doc_id,
                "schema_id": schema.schema_id,
                "schema_version": schema.version,
                "template_id": template.template_id,
                "template_version": template.version,
                "document_metadata": document_metadata,
                "metadata_template": metadata_template_ref,
                "metadata_field_trace": (
                    metadata_result.report.model_dump(mode="json")["field_traces"]
                    if metadata_result is not None
                    else []
                ),
                "features": features,
                "document_summary": (
                    document_summary.model_dump(mode="json")
                    if document_summary is not None
                    else None
                ),
                "artifact_roles": {
                    "content.json": "structured_json",
                    "content.md": "markdown",
                    "chunks.jsonl": "chunks",
                    "mapping_report.json": "mapping_report",
                    "transform_report.json": "transform_report",
                    "validation_report.json": "validation_report",
                    "content_organization_report.json": "content_organization_report",
                    "canonical.json": "canonical",
                    "metadata.json": "package_metadata",
                },
            },
        }
        if metadata_result is not None:
            files["metadata_template_report.json"] = metadata_result.report.model_dump(
                mode="json"
            )
            files["metadata.json"]["artifact_roles"]["metadata_template_report.json"] = (
                "metadata_template_report"
            )
        if artifact_consistency_report is not None:
            files["artifact_consistency_report.json"] = (
                artifact_consistency_report.model_dump(mode="json")
            )
            files["metadata.json"]["artifact_roles"][
                "artifact_consistency_report.json"
            ] = "artifact_consistency_report"
        optional_paths: set[str] = set()
        if include_assertion_report and conversion_assertion_report is not None:
            assertion_path = "reports/conversion_assertion_report.json"
            files[assertion_path] = conversion_assertion_report
            optional_paths.add(assertion_path)
            files["metadata.json"]["artifact_roles"][assertion_path] = (
                "conversion_assertion_report"
            )
        written_files: list[Path] = []
        for name, payload in files.items():
            path = package_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            written_files.append(path)

        markdown_path = package_dir / "content.md"
        markdown_path.write_text(rendered.markdown, encoding="utf-8")
        written_files.append(markdown_path)

        chunks_path = package_dir / "chunks.jsonl"
        chunks_path.write_text(
            "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in rendered.chunks),
            encoding="utf-8",
        )
        written_files.append(chunks_path)

        manifest = ManifestService().build_manifest(
            package_id=package_id,
            package_version="1.0.0",
            task_id=task_id,
            doc_id=doc_id,
            schema=schema,
            template_id=template.template_id,
            package_dir=package_dir,
            file_paths=written_files,
            optional_paths=optional_paths,
        )
        manifest_path = package_dir / "manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        verifier_report = PackageVerifierService().verify_package(package_dir)
        verifier_path = package_dir / "verifier_report.json"
        verifier_path.write_text(
            verifier_report.model_dump_json(indent=2),
            encoding="utf-8",
        )

        final_manifest_files = [*written_files, verifier_path]
        manifest = ManifestService().build_manifest(
            package_id=package_id,
            package_version="1.0.0",
            task_id=task_id,
            doc_id=doc_id,
            schema=schema,
            template_id=template.template_id,
            package_dir=package_dir,
            file_paths=final_manifest_files,
            optional_paths=optional_paths,
        )
        manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )
        verifier_report = PackageVerifierService().verify_package(package_dir)

        zip_path = package_dir / "standard_package.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package_dir.rglob("*")):
                if path.is_file() and path.name != "standard_package.zip":
                    archive.write(path, path.relative_to(package_dir).as_posix())

        metadata = OutputPackageMetadata(
            package_id=package_id,
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema.schema_id,
            template_id=template.template_id,
            package_version="1.0.0",
            zip_path=str(zip_path),
            status="completed" if verifier_report.passed else "failed",
            sha256=ManifestService.sha256_file(zip_path),
            created_at=manifest.created_at,
        )
        return PackageResult(
            metadata=metadata,
            verifier_report=verifier_report,
            manifest=manifest,
        )
