from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.schemas.artifact_consistency import ArtifactConsistencyReport
from app.schemas.canonical import CanonicalModel
from app.schemas.content_organization import ContentOrganizationReport
from app.schemas.document_summary import DocumentSummary
from app.schemas.mapping_template import MappingTemplate
from app.schemas.metadata_template import MetadataRenderResult, MetadataTemplateConfig
from app.schemas.package import Manifest, OutputPackageMetadata
from app.schemas.reports import ConsistencyReport, MappingReport, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.services.artifact_consistency_service import ArtifactConsistencyService
from app.services.manifest_service import ManifestService
from app.services.package_verifier_service import PackageVerifierService
from app.services.render_service import RenderedArtifacts


@dataclass(frozen=True)
class PackageResult:
    metadata: OutputPackageMetadata
    verifier_report: ConsistencyReport
    manifest: Manifest


class PackageBuildError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


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
        packages_root = self.output_root / "packages"
        temp_root = packages_root / ".tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{package_id}-", dir=temp_root))
        final_dir = packages_root / package_id
        current_stage = "content_write"
        try:
            report = artifact_consistency_report or ArtifactConsistencyService().verify(
                canonical=canonical,
                structured_json=rendered.structured_json,
                markdown=rendered.markdown,
                chunks=rendered.chunks,
                document_summary=document_summary,
                block_exclusions=self._report_exclusions(content_organization_report),
            )
            files, optional_paths = self._semantic_files(
                package_id=package_id,
                task_id=task_id,
                doc_id=doc_id,
                schema=schema,
                template=template,
                canonical=canonical,
                rendered=rendered,
                mapping_report=mapping_report,
                transform_report=transform_report,
                validation_report=validation_report,
                content_organization_report=content_organization_report,
                conversion_assertion_report=conversion_assertion_report,
                include_assertion_report=include_assertion_report,
                metadata_result=metadata_result,
                metadata_template=metadata_template,
                document_summary=document_summary,
                artifact_consistency_report=report,
            )
            written_files = self._write_semantic_files(temp_dir, files, rendered)
            current_stage = "manifest_write"
            manifest = ManifestService().build_manifest(
                package_id=package_id,
                package_version="1.0.0",
                task_id=task_id,
                doc_id=doc_id,
                schema=schema,
                template_id=template.template_id,
                package_dir=temp_dir,
                file_paths=written_files,
                optional_paths=optional_paths,
            )
            manifest_path = temp_dir / "manifest.json"
            self._atomic_write_text(manifest_path, manifest.model_dump_json(indent=2))
            current_stage = "package_verify"
            verifier_report = PackageVerifierService().verify_package(
                temp_dir, strict=True
            )
            self._atomic_write_text(
                temp_dir / "verifier_report.json",
                verifier_report.model_dump_json(indent=2),
            )
            manifest_hash = ManifestService.sha256_file(manifest_path)
            verifier_hash = ManifestService.sha256_file(
                temp_dir / "verifier_report.json"
            )
            if not verifier_report.passed:
                return PackageResult(
                    metadata=OutputPackageMetadata(
                        package_id=package_id,
                        task_id=task_id,
                        doc_id=doc_id,
                        schema_id=schema.schema_id,
                        template_id=template.template_id,
                        package_version="1.0.0",
                        zip_path=str(final_dir / "standard_package.zip"),
                        status="failed",
                        created_at=manifest.created_at,
                        manifest_sha256=manifest_hash,
                        verifier_report_sha256=verifier_hash,
                    ),
                    verifier_report=verifier_report,
                    manifest=manifest,
                )
            current_stage = "zip_create"
            zip_path = temp_dir / "standard_package.zip"
            self._write_deterministic_zip(temp_dir, zip_path)
            zip_hash = ManifestService.sha256_file(zip_path)
            current_stage = "final_rename"
            self._finalize_directory(temp_dir, final_dir, temp_root)
            final_zip_path = final_dir / "standard_package.zip"
            metadata = OutputPackageMetadata(
                package_id=package_id,
                task_id=task_id,
                doc_id=doc_id,
                schema_id=schema.schema_id,
                template_id=template.template_id,
                package_version="1.0.0",
                zip_path=str(final_zip_path),
                status="completed",
                sha256=zip_hash,
                manifest_sha256=manifest_hash,
                verifier_report_sha256=verifier_hash,
                zip_sha256=zip_hash,
                created_at=manifest.created_at,
            )
            return PackageResult(
                metadata=metadata,
                verifier_report=verifier_report,
                manifest=manifest,
            )
        except PackageBuildError:
            raise
        except Exception as exc:
            raise PackageBuildError(current_stage, str(exc)) from exc
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _report_exclusions(report: ContentOrganizationReport) -> list[dict]:
        options = report.summary.get("options", {})
        exclusions = options.get("block_exclusions", []) if isinstance(options, dict) else []
        return exclusions if isinstance(exclusions, list) else []

    @staticmethod
    def _semantic_files(
        *,
        package_id: str,
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
        conversion_assertion_report: dict | None,
        include_assertion_report: bool,
        metadata_result: MetadataRenderResult | None,
        metadata_template: MetadataTemplateConfig | None,
        document_summary: DocumentSummary | None,
        artifact_consistency_report: ArtifactConsistencyReport,
    ) -> tuple[dict[str, object], set[str]]:
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
        features = ["artifact_consistency_v1"]
        if metadata_result is not None:
            features.append("metadata_template_v1")
        if document_summary is not None:
            features.append("document_summary_v1")
        artifact_roles = {
            "content.json": "structured_json",
            "content.md": "markdown",
            "chunks.jsonl": "chunks",
            "mapping_report.json": "mapping_report",
            "transform_report.json": "transform_report",
            "validation_report.json": "validation_report",
            "content_organization_report.json": "content_organization_report",
            "canonical.json": "canonical",
            "metadata.json": "package_metadata",
            "artifact_consistency_report.json": "artifact_consistency_report",
        }
        files: dict[str, object] = {
            "content.json": rendered.structured_json,
            "mapping_report.json": mapping_report.model_dump(mode="json"),
            "transform_report.json": transform_report,
            "validation_report.json": validation_report.model_dump(mode="json"),
            "content_organization_report.json": content_organization_report.model_dump(
                mode="json"
            ),
            "canonical.json": canonical.model_dump(mode="json"),
            "artifact_consistency_report.json": artifact_consistency_report.model_dump(
                mode="json"
            ),
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
                "artifact_roles": artifact_roles,
            },
        }
        if metadata_result is not None:
            files["metadata_template_report.json"] = metadata_result.report.model_dump(
                mode="json"
            )
            artifact_roles["metadata_template_report.json"] = "metadata_template_report"
        optional_paths: set[str] = set()
        if include_assertion_report and conversion_assertion_report is not None:
            assertion_path = "reports/conversion_assertion_report.json"
            files[assertion_path] = conversion_assertion_report
            optional_paths.add(assertion_path)
            artifact_roles[assertion_path] = "conversion_assertion_report"
        return files, optional_paths

    @classmethod
    def _write_semantic_files(
        cls,
        package_dir: Path,
        files: dict[str, object],
        rendered: RenderedArtifacts,
    ) -> list[Path]:
        written: list[Path] = []
        for name, payload in files.items():
            path = package_dir / name
            cls._atomic_write_text(
                path,
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            )
            written.append(path)
        markdown_path = package_dir / "content.md"
        cls._atomic_write_text(markdown_path, rendered.markdown)
        written.append(markdown_path)
        chunks_path = package_dir / "chunks.jsonl"
        cls._atomic_write_text(
            chunks_path,
            "\n".join(
                json.dumps(chunk, ensure_ascii=False, sort_keys=True)
                for chunk in rendered.chunks
            ),
        )
        written.append(chunks_path)
        return written

    @staticmethod
    def _atomic_write_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _write_deterministic_zip(cls, package_dir: Path, zip_path: Path) -> None:
        temporary = zip_path.with_name(f".{zip_path.name}.{uuid.uuid4().hex}.tmp")
        try:
            paths = sorted(
                path
                for path in package_dir.rglob("*")
                if path.is_file()
                and path != temporary
                and path.name != "standard_package.zip"
            )
            with zipfile.ZipFile(
                temporary, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for path in paths:
                    archive_name = path.relative_to(package_dir).as_posix()
                    pure = PurePosixPath(archive_name)
                    if (
                        pure.is_absolute()
                        or ".." in pure.parts
                        or "\\" in archive_name
                        or str(pure) != archive_name
                    ):
                        raise PackageBuildError(
                            "zip_create", f"unsafe ZIP entry: {archive_name}"
                        )
                    info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes())
            with temporary.open("rb") as handle:
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    # Windows may reject fsync on a read-only descriptor.
                    pass
            os.replace(temporary, zip_path)
        except PackageBuildError:
            raise
        except Exception as exc:
            raise PackageBuildError("zip_create", str(exc)) from exc
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _finalize_directory(temp_dir: Path, final_dir: Path, temp_root: Path) -> None:
        backup = temp_root / f"{final_dir.name}-backup-{uuid.uuid4().hex}"
        moved_prior = False
        completed = False
        try:
            if final_dir.exists():
                os.replace(final_dir, backup)
                moved_prior = True
            os.replace(temp_dir, final_dir)
            completed = True
        except Exception as exc:
            if moved_prior and backup.exists() and not final_dir.exists():
                try:
                    os.replace(backup, final_dir)
                except Exception as rollback_exc:
                    raise PackageBuildError(
                        "final_rename",
                        f"{exc}; prior package preserved at {backup}: {rollback_exc}",
                    ) from exc
            raise PackageBuildError("final_rename", str(exc)) from exc
        finally:
            if completed and backup.exists():
                shutil.rmtree(backup, ignore_errors=True)
