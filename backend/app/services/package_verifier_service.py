import json
from pathlib import Path

from app.schemas.package import Manifest
from app.schemas.reports import ConsistencyReport, ReportIssue
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

    def verify_package(self, package_dir: str | Path, *, strict: bool = False) -> ConsistencyReport:
        package_path = Path(package_dir)
        manifest_path = package_path / "manifest.json"
        errors: list[ReportIssue] = []
        warnings: list[ReportIssue] = []

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

        manifest = Manifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
        manifest_paths = {file.path for file in manifest.files}
        for required_file in self.REQUIRED_FILES:
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
                    level="error" if strict else "warning",
                    message="Required file is not listed in manifest.",
                    path=required_file,
                    code="required_file_not_manifested",
                )
                if strict:
                    errors.append(issue)
                else:
                    warnings.append(issue)

        for file_info in manifest.files:
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
            if path.is_file() and ManifestService.sha256_file(path) != file_info.sha256:
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

        self._check_json(package_path / "content.json", "content_json_invalid", errors)
        self._check_json(package_path / "metadata.json", "metadata_json_invalid", errors)
        self._check_json(
            package_path / "content_organization_report.json",
            "content_organization_report_invalid",
            errors,
        )
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
            checks=[],
            errors=errors,
            warnings=warnings,
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
