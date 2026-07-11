from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
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
    artifact_consistency_report: ArtifactConsistencyReport


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
                block_exclusion_rule_ids=self._report_exclusion_rule_ids(
                    content_organization_report
                ),
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
            report = self._bind_artifact_consistency_report(temp_dir, report)
            PackageService._atomic_write_text(
                temp_dir / "artifact_consistency_report.json",
                json.dumps(
                    report.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
            )
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
                        zip_path=None,
                        status="failed",
                        created_at=manifest.created_at,
                        manifest_sha256=manifest_hash,
                        verifier_report_sha256=verifier_hash,
                    ),
                    verifier_report=verifier_report,
                    manifest=manifest,
                    artifact_consistency_report=report,
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
                artifact_consistency_report=report,
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
    def _report_exclusion_rule_ids(report: ContentOrganizationReport) -> set[str]:
        options = report.summary.get("options", {})
        rules = (
            options.get("block_exclusion_rules", [])
            if isinstance(options, dict)
            else []
        )
        return {
            str(rule.get("rule_id"))
            for rule in rules
            if isinstance(rule, dict) and str(rule.get("rule_id") or "").strip()
        }

    @staticmethod
    def _bind_artifact_consistency_report(
        package_dir: Path, report: ArtifactConsistencyReport
    ) -> ArtifactConsistencyReport:
        names = (
            "canonical.json",
            "content.json",
            "content.md",
            "chunks.jsonl",
            "metadata.json",
        )
        hashes = {
            name: ManifestService.sha256_file(package_dir / name) for name in names
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                hashes,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return report.model_copy(
            update={
                "artifact_input_hashes": hashes,
                "artifact_input_fingerprint": fingerprint,
            }
        )

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
            paths = cls._safe_package_files(package_dir)
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
                    archive.writestr(info, cls._read_regular_file(path))
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
        del temp_root
        if final_dir.exists():
            raise PackageBuildError(
                "final_rename", "a verified package with this package_id already exists"
            )
        try:
            # Unlike os.replace, rename will not destructively replace a non-empty
            # package directory if one appears concurrently.
            os.rename(temp_dir, final_dir)
        except Exception as exc:
            raise PackageBuildError("final_rename", str(exc)) from exc

    @classmethod
    def _safe_package_files(cls, package_dir: Path) -> list[Path]:
        root = package_dir.resolve(strict=True)
        files: list[Path] = []
        for path in package_dir.rglob("*"):
            if cls._is_link_or_reparse(path):
                raise PackageBuildError("zip_create", f"unsafe linked entry: {path}")
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                raise PackageBuildError("zip_create", str(exc)) from exc
            if root not in resolved.parents and resolved != root:
                raise PackageBuildError("zip_create", f"entry escapes package root: {path}")
            if path.is_file() and path.name != "standard_package.zip":
                files.append(path)
        return sorted(files, key=lambda path: path.relative_to(package_dir).as_posix())

    @staticmethod
    def _is_link_or_reparse(path: Path) -> bool:
        try:
            details = path.lstat()
        except OSError:
            return True
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        file_attributes = getattr(details, "st_file_attributes", 0)
        return stat.S_ISLNK(details.st_mode) or bool(file_attributes & reparse_flag)

    @classmethod
    def _read_regular_file(cls, path: Path) -> bytes:
        if cls._is_link_or_reparse(path):
            raise PackageBuildError("zip_create", f"unsafe linked entry: {path}")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode):
                raise PackageBuildError("zip_create", f"entry is not regular: {path}")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read()
        finally:
            os.close(descriptor)
        if cls._is_link_or_reparse(path):
            raise PackageBuildError("zip_create", f"entry changed during read: {path}")
        return data
