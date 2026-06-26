import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.schemas.canonical import CanonicalModel
from app.schemas.content_organization import ContentOrganizationReport
from app.schemas.mapping_template import MappingTemplate
from app.schemas.package import OutputPackageMetadata
from app.schemas.reports import ConsistencyReport, MappingReport, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.services.manifest_service import ManifestService
from app.services.package_verifier_service import PackageVerifierService
from app.services.render_service import RenderedArtifacts


@dataclass(frozen=True)
class PackageResult:
    metadata: OutputPackageMetadata
    verifier_report: ConsistencyReport


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
    ) -> PackageResult:
        package_id = f"pkg_{task_id}"
        package_dir = self.output_root / "packages" / package_id
        package_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "content.json": rendered.structured_json,
            "mapping_report.json": mapping_report.model_dump(mode="json"),
            "transform_report.json": transform_report,
            "validation_report.json": validation_report.model_dump(mode="json"),
            "content_organization_report.json": content_organization_report.model_dump(mode="json"),
            "canonical.json": canonical.model_dump(mode="json"),
        }
        written_files: list[Path] = []
        for name, payload in files.items():
            path = package_dir / name
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

        zip_path = package_dir / "standard_package.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package_dir.iterdir()):
                if path.is_file() and path.name != "standard_package.zip":
                    archive.write(path, path.name)

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
        return PackageResult(metadata=metadata, verifier_report=verifier_report)
