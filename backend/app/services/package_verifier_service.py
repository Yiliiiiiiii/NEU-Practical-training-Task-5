import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath

from app.schemas.artifact_consistency import ArtifactConsistencyReport
from app.schemas.canonical import CanonicalModel
from app.schemas.document_summary import DocumentSummary
from app.schemas.metadata_template import MetadataTemplateReport
from app.schemas.package import Manifest
from app.schemas.reports import ConsistencyCheck, ConsistencyReport, ReportIssue
from app.services.artifact_consistency_service import ArtifactConsistencyService
from app.services.manifest_service import ManifestService


class PackageVerifierService:
    REQUIRED_FILES = {
        "content.json",
        "content.md",
        "chunks.jsonl",
        "mapping_report.json",
        "validation_report.json",
        "content_organization_report.json",
        "metadata.json",
        "manifest.json",
    }
    STRICT_REQUIRED_FILES = {
        "canonical.json",
        "transform_report.json",
        "artifact_consistency_report.json",
    }
    MANIFEST_EXCLUDED_FILES = {
        "manifest.json",
        "verifier_report.json",
        "standard_package.zip",
    }

    def verify_package(self, package_dir: str | Path, *, strict: bool = False) -> ConsistencyReport:
        package_path = Path(package_dir)
        manifest_path = package_path / "manifest.json"
        errors: list[ReportIssue] = []
        warnings: list[ReportIssue] = []
        actual_files = self._scan_package_tree(package_path, errors)
        if any(issue.code == "package_link_unsafe" for issue in errors):
            return ConsistencyReport(task_id="unknown", passed=False, errors=errors)

        if not manifest_path.is_file():
            return ConsistencyReport(
                task_id="unknown",
                passed=False,
                checks=[],
                errors=[
                    ReportIssue(
                        level="error",
                        message="manifest.json is missing.",
                        path="manifest.json",
                        code="manifest_missing",
                    )
                ],
                warnings=[],
            )

        try:
            manifest = Manifest.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except (ValueError, TypeError) as exc:
            return ConsistencyReport(
                task_id="unknown",
                passed=False,
                errors=[
                    ReportIssue(
                        level="error",
                        message=str(exc),
                        path="manifest.json",
                        code="manifest_invalid",
                    )
                ],
                manifest_sha256=ManifestService.sha256_file(manifest_path),
            )
        manifest_sha256 = ManifestService.sha256_file(manifest_path)
        self._check_stored_verifier_manifest_binding(
            package_path, manifest_sha256, errors
        )
        self._check_manifest_paths(manifest, errors)
        manifest_paths = {file.path for file in manifest.files}
        feature_files = self._feature_required_files(package_path, errors)
        required_files = self.REQUIRED_FILES | feature_files
        if strict:
            required_files |= self.STRICT_REQUIRED_FILES
        for required_file in required_files:
            if required_file == "manifest.json":
                continue
            if not (package_path / required_file).is_file():
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Required file is missing.",
                        path=required_file,
                        code="required_file_missing",
                    )
                )
            if required_file not in manifest_paths:
                issue = ReportIssue(
                    level="error" if strict or required_file in feature_files else "warning",
                    message="Required file is not listed in manifest.",
                    path=required_file,
                    code="required_file_not_manifested",
                )
                if strict or required_file in feature_files:
                    errors.append(issue)
                else:
                    warnings.append(issue)

        for file_info in manifest.files:
            if not self._is_safe_manifest_path(file_info.path):
                continue
            path = package_path / file_info.path
            if file_info.required and not path.is_file():
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Required file is missing.",
                        path=file_info.path,
                        code="required_file_missing",
                    )
                )
                continue
            actual_sha256 = (
                self._sha256_regular_file(path, package_path, errors)
                if path.is_file()
                else None
            )
            if path.is_file() and actual_sha256 != file_info.sha256:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="File checksum does not match manifest.",
                        path=file_info.path,
                        code="checksum_mismatch",
                    )
                )
            if strict and path.is_file() and path.stat().st_size != file_info.bytes:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="File byte size does not match manifest.",
                        path=file_info.path,
                        code="byte_size_mismatch",
                    )
                )
            if strict and file_info.media_type != ManifestService.media_type(file_info.path):
                errors.append(
                    ReportIssue(
                        level="error",
                        message="File media type does not match package spec.",
                        path=file_info.path,
                        code="media_type_mismatch",
                    )
                )
            if strict and file_info.role != ManifestService.role(file_info.path):
                errors.append(
                    ReportIssue(
                        level="error",
                        message="File role does not match package spec.",
                        path=file_info.path,
                        code="role_mismatch",
                    )
                )

        if strict:
            for actual_path in sorted(actual_files - self.MANIFEST_EXCLUDED_FILES):
                if actual_path not in manifest_paths:
                    errors.append(
                        ReportIssue(
                            level="error",
                            message="Package file is not covered by the manifest.",
                            path=actual_path,
                            code="unmanifested_file",
                        )
                    )

        self._check_json(package_path / "content.json", "content_json_invalid", errors)
        self._check_json(package_path / "metadata.json", "metadata_json_invalid", errors)
        self._check_json(
            package_path / "content_organization_report.json",
            "content_organization_report_invalid",
            errors,
        )
        if "metadata_template_report.json" in feature_files:
            self._check_metadata_template_report(
                package_path / "metadata_template_report.json", errors
            )
        if "artifact_consistency_report.json" in feature_files:
            self._check_artifact_consistency_report(
                package_path / "artifact_consistency_report.json", errors
            )
            self._recompute_artifact_consistency(package_path, errors)
        self._check_jsonl(package_path / "chunks.jsonl", "chunks_jsonl_invalid", errors)
        markdown_path = package_path / "content.md"
        if markdown_path.is_file() and not markdown_path.read_text(encoding="utf-8").strip():
            errors.append(
                ReportIssue(
                    level="error",
                    message="Markdown output is empty.",
                    path="content.md",
                    code="markdown_empty",
                )
            )

        return ConsistencyReport(
            task_id=manifest.task_id,
            passed=not errors,
            checks=[
                ConsistencyCheck(
                    check_name="artifact_consistency_report_identity",
                    passed=(package_path / "artifact_consistency_report.json").is_file(),
                    details={
                        "sha256": (
                            self._sha256_regular_file(
                                package_path / "artifact_consistency_report.json",
                                package_path,
                                [],
                            )
                            if (package_path / "artifact_consistency_report.json").is_file()
                            else None
                        )
                    },
                )
            ],
            errors=errors,
            warnings=warnings,
            manifest_sha256=manifest_sha256,
        )

    @classmethod
    def _scan_package_tree(
        cls, package_path: Path, errors: list[ReportIssue]
    ) -> set[str]:
        actual_files: set[str] = set()
        if not package_path.exists() or cls._is_link_or_reparse(package_path):
            errors.append(
                ReportIssue(
                    level="error",
                    message="Package root is missing or is a link/reparse point.",
                    path=str(package_path),
                    code="package_link_unsafe",
                )
            )
            return actual_files
        root = package_path.resolve(strict=True)
        for path in package_path.rglob("*"):
            relative = path.relative_to(package_path).as_posix()
            if cls._is_link_or_reparse(path):
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Package contains a link or reparse point.",
                        path=relative,
                        code="package_link_unsafe",
                    )
                )
                continue
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                errors.append(
                    ReportIssue(
                        level="error",
                        message=str(exc),
                        path=relative,
                        code="package_entry_unsafe",
                    )
                )
                continue
            if root not in resolved.parents and resolved != root:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Package entry escapes the package root.",
                        path=relative,
                        code="package_entry_unsafe",
                    )
                )
            elif path.is_file():
                actual_files.add(relative)
        return actual_files

    @classmethod
    def _check_stored_verifier_manifest_binding(
        cls,
        package_path: Path,
        manifest_sha256: str,
        errors: list[ReportIssue],
    ) -> None:
        verifier_path = package_path / "verifier_report.json"
        if not verifier_path.is_file():
            return
        try:
            stored = ConsistencyReport.model_validate_json(
                cls._read_regular_file(verifier_path, package_path)
            )
        except (OSError, ValueError, TypeError) as exc:
            errors.append(
                ReportIssue(
                    level="error",
                    message=str(exc),
                    path="verifier_report.json",
                    code="stored_verifier_invalid",
                )
            )
            return
        if stored.manifest_sha256 != manifest_sha256:
            errors.append(
                ReportIssue(
                    level="error",
                    message="Stored verifier report is bound to a different manifest.",
                    path="verifier_report.json",
                    code="verifier_manifest_binding_mismatch",
                )
            )

    @staticmethod
    def _is_link_or_reparse(path: Path) -> bool:
        try:
            details = path.lstat()
        except OSError:
            return True
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return stat.S_ISLNK(details.st_mode) or bool(
            getattr(details, "st_file_attributes", 0) & reparse_flag
        )

    @classmethod
    def _read_regular_file(cls, path: Path, package_root: Path) -> bytes:
        root = package_root.resolve(strict=True)
        if cls._is_link_or_reparse(path):
            raise OSError(f"unsafe linked package entry: {path}")
        resolved = path.resolve(strict=True)
        if root not in resolved.parents:
            raise OSError(f"package entry escapes root: {path}")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            details = os.fstat(descriptor)
            if not stat.S_ISREG(details.st_mode):
                raise OSError(f"package entry is not regular: {path}")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read()
        finally:
            os.close(descriptor)
        if cls._is_link_or_reparse(path):
            raise OSError(f"package entry changed during read: {path}")
        return data

    @classmethod
    def _sha256_regular_file(
        cls, path: Path, package_root: Path, errors: list[ReportIssue]
    ) -> str | None:
        try:
            return hashlib.sha256(cls._read_regular_file(path, package_root)).hexdigest()
        except OSError as exc:
            errors.append(
                ReportIssue(
                    level="error",
                    message=str(exc),
                    path=path.name,
                    code="package_entry_unsafe",
                )
            )
            return None

    @staticmethod
    def _check_manifest_paths(
        manifest: Manifest, errors: list[ReportIssue]
    ) -> None:
        seen: set[str] = set()
        excluded = {"manifest.json", "verifier_report.json", "standard_package.zip"}
        for file_info in manifest.files:
            value = file_info.path
            safe = PackageVerifierService._is_safe_manifest_path(value)
            if not safe:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Manifest path is not a safe normalized relative path.",
                        path=value,
                        code="manifest_path_unsafe",
                    )
                )

            if value in seen:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Manifest path is duplicated.",
                        path=value,
                        code="manifest_path_duplicate",
                    )
                )
            if value in excluded:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="Manifest contains a self-referential or finalization artifact.",
                        path=value,
                        code="manifest_path_excluded",
                    )
                )
            seen.add(value)

    @staticmethod
    def _is_safe_manifest_path(value: str) -> bool:
        path = PurePosixPath(value)
        return (
            bool(value)
            and "\\" not in value
            and not path.is_absolute()
            and ":" not in value
            and ".." not in path.parts
            and str(path) == value
        )

    @classmethod
    def _recompute_artifact_consistency(
        cls, package_path: Path, errors: list[ReportIssue]
    ) -> None:
        try:
            input_names = (
                "canonical.json",
                "content.json",
                "content.md",
                "chunks.jsonl",
                "metadata.json",
            )
            input_bytes = {
                name: cls._read_regular_file(package_path / name, package_path)
                for name in input_names
            }
            input_hashes = {
                name: hashlib.sha256(value).hexdigest()
                for name, value in input_bytes.items()
            }
            input_fingerprint = hashlib.sha256(
                json.dumps(
                    input_hashes,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            canonical = CanonicalModel.model_validate_json(
                input_bytes["canonical.json"]
            )
            structured = json.loads(input_bytes["content.json"])
            markdown = input_bytes["content.md"].decode("utf-8")
            chunks = [
                json.loads(line)
                for line in input_bytes["chunks.jsonl"].decode("utf-8").splitlines()
                if line.strip()
            ]
            metadata = json.loads(input_bytes["metadata.json"])
            organization = json.loads(
                (package_path / "content_organization_report.json").read_text(
                    encoding="utf-8"
                )
            )
            summary_payload = metadata.get("document_summary")
            summary = (
                DocumentSummary.model_validate(summary_payload)
                if isinstance(summary_payload, dict) and summary_payload
                else None
            )
            raw_options = organization.get("summary", {}).get("options", {})
            exclusions = (
                raw_options.get("block_exclusions", [])
                if isinstance(raw_options, dict)
                else []
            )
            exclusion_rules = (
                raw_options.get("block_exclusion_rules", [])
                if isinstance(raw_options, dict)
                else []
            )
            stored = ArtifactConsistencyReport.model_validate_json(
                (package_path / "artifact_consistency_report.json").read_text(
                    encoding="utf-8"
                )
            )
            recomputed = ArtifactConsistencyService().verify(
                canonical=canonical,
                structured_json=structured,
                markdown=markdown,
                chunks=chunks,
                document_summary=summary,
                block_exclusions=exclusions if isinstance(exclusions, list) else [],
                block_exclusion_rule_ids={
                    str(rule.get("rule_id"))
                    for rule in exclusion_rules
                    if isinstance(rule, dict)
                    and str(rule.get("rule_id") or "").strip()
                },
            )
            recomputed = recomputed.model_copy(
                update={
                    "artifact_input_hashes": input_hashes,
                    "artifact_input_fingerprint": input_fingerprint,
                }
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(
                ReportIssue(
                    level="error",
                    message=str(exc),
                    path="artifact_consistency_report.json",
                    code="artifact_consistency_recompute_error",
                )
            )
            return
        if (
            stored.artifact_input_hashes != input_hashes
            or stored.artifact_input_fingerprint != input_fingerprint
        ):
            errors.append(
                ReportIssue(
                    level="error",
                    message="Packaged artifact inputs do not match the bound report inputs.",
                    path="artifact_consistency_report.json",
                    code="artifact_input_binding_mismatch",
                )
            )
        if not recomputed.passed:
            errors.append(
                ReportIssue(
                    level="error",
                    message="Artifact consistency failed when recomputed from package files.",
                    path="artifact_consistency_report.json",
                    code="artifact_consistency_recomputed_failed",
                )
            )
        if stored.model_dump(mode="json") != recomputed.model_dump(mode="json"):
            errors.append(
                ReportIssue(
                    level="error",
                    message="Stored artifact consistency report is stale.",
                    path="artifact_consistency_report.json",
                    code="artifact_consistency_report_stale",
                )
            )

    @staticmethod
    def _feature_required_files(
        package_path: Path, errors: list[ReportIssue]
    ) -> set[str]:
        metadata_path = package_path / "metadata.json"
        if not metadata_path.is_file():
            return set()
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return set()
        features = metadata.get("features", []) if isinstance(metadata, dict) else []
        if not isinstance(features, list) or not all(
            isinstance(item, str) for item in features
        ):
            errors.append(
                ReportIssue(
                    level="error",
                    message="metadata features must be a string array.",
                    path="metadata.json.features",
                    code="package_features_invalid",
                )
            )
            return set()
        required: set[str] = set()
        if "metadata_template_v1" in features:
            required.add("metadata_template_report.json")
        if "artifact_consistency_v1" in features:
            required.add("artifact_consistency_report.json")
        return required

    @staticmethod
    def _check_artifact_consistency_report(
        path: Path, errors: list[ReportIssue]
    ) -> None:
        if not path.is_file():
            return
        try:
            report = ArtifactConsistencyReport.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (ValueError, TypeError) as exc:
            errors.append(
                ReportIssue(
                    level="error",
                    message=str(exc),
                    path=path.name,
                    code="artifact_consistency_report_invalid",
                )
            )
            return
        if not report.passed:
            errors.append(
                ReportIssue(
                    level="error",
                    message="Artifact consistency report did not pass.",
                    path=path.name,
                    code="artifact_consistency_failed",
                )
            )

    @staticmethod
    def _check_metadata_template_report(
        path: Path, errors: list[ReportIssue]
    ) -> None:
        if not path.is_file():
            return
        try:
            MetadataTemplateReport.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, TypeError) as exc:
            errors.append(
                ReportIssue(
                    level="error",
                    message=str(exc),
                    path=path.name,
                    code="metadata_template_report_invalid",
                )
            )

    @staticmethod
    def _check_json(path: Path, code: str, errors: list[ReportIssue]) -> None:
        if not path.is_file():
            return
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(
                ReportIssue(level="error", message=str(exc), path=path.name, code=code)
            )

    @staticmethod
    def _check_jsonl(path: Path, code: str, errors: list[ReportIssue]) -> None:
        if not path.is_file():
            return
        try:
            parsed_rows = []
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if line.strip():
                    row = json.loads(line)
                    parsed_rows.append(row)
                    PackageVerifierService._check_chunk_row(row, line_number, errors)
            if not parsed_rows:
                errors.append(
                    ReportIssue(
                        level="error",
                        message="chunks.jsonl does not contain any chunks.",
                        path=path.name,
                        code="chunks_jsonl_empty",
                    )
                )
        except json.JSONDecodeError as exc:
            errors.append(
                ReportIssue(level="error", message=str(exc), path=path.name, code=code)
            )

    @staticmethod
    def _check_chunk_row(row: object, line_number: int, errors: list[ReportIssue]) -> None:
        path = f"chunks.jsonl:{line_number}"
        if not isinstance(row, dict):
            errors.append(
                ReportIssue(
                    level="error",
                    message="Chunk row must be a JSON object.",
                    path=path,
                    code="chunk_row_invalid",
                )
            )
            return

        checks = [
            (bool(row.get("chunk_id")), "chunk_id is required.", "chunk_id_missing"),
            ("text" in row, "text field is required.", "chunk_text_missing"),
            (isinstance(row.get("tags"), dict), "tags object is required.", "chunk_tags_missing"),
            (
                isinstance(row.get("keywords"), list),
                "keywords list is required.",
                "chunk_keywords_missing",
            ),
            (
                isinstance(row.get("summary"), str),
                "summary string is required.",
                "chunk_summary_missing",
            ),
            (
                bool(row.get("source_block_ids")) or bool(row.get("source_links")),
                "source_block_ids or source_links are required.",
                "chunk_source_links_missing",
            ),
        ]
        for passed, message, code in checks:
            if not passed:
                errors.append(
                    ReportIssue(
                        level="error",
                        message=message,
                        path=path,
                        code=code,
                    )
                )
