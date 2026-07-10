import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.package import Manifest, ManifestFile
from app.schemas.target_schema import TargetSchema


class ManifestService:
    def build_manifest(
        self,
        package_id: str,
        package_version: str,
        task_id: str,
        doc_id: str,
        schema: TargetSchema,
        template_id: str,
        package_dir: Path,
        file_paths: list[Path],
        optional_paths: set[str] | None = None,
    ) -> Manifest:
        optional_paths = optional_paths or set()
        return Manifest(
            manifest_version="1.1",
            package_id=package_id,
            package_version=package_version,
            task_id=task_id,
            doc_id=doc_id,
            created_at=datetime.now(UTC).isoformat(),
            files=[
                ManifestFile(
                    path=path.relative_to(package_dir).as_posix(),
                    required=path.relative_to(package_dir).as_posix()
                    not in optional_paths,
                    media_type=self.media_type(path.relative_to(package_dir).as_posix()),
                    sha256=self.sha256_file(path),
                    bytes=path.stat().st_size,
                    role=self.role(path.relative_to(package_dir).as_posix()),
                )
                for path in sorted(file_paths)
            ],
            generator={
                "name": "SchemaPack Agent",
                "version": "service-layer-0.1.0",
                "schema_id": schema.schema_id,
                "schema_version": schema.version,
                "template_id": template_id,
            },
        )

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def media_type(file_name: str) -> str:
        if file_name.endswith(".json"):
            return "application/json"
        if file_name.endswith(".jsonl"):
            return "application/jsonl"
        if file_name.endswith(".md"):
            return "text/markdown"
        return "application/octet-stream"

    @staticmethod
    def role(file_name: str) -> str:
        file_name = Path(file_name).name
        return {
            "content.json": "structured_json",
            "content.md": "markdown",
            "chunks.jsonl": "chunks",
            "mapping_report.json": "mapping_report",
            "transform_report.json": "transform_report",
            "validation_report.json": "validation_report",
            "content_organization_report.json": "content_organization_report",
            "metadata_template_report.json": "metadata_template_report",
            "metadata.json": "package_metadata",
            "canonical.json": "canonical",
            "verifier_report.json": "verifier_report",
            "conversion_assertion_report.json": "conversion_assertion_report",
        }.get(file_name, "supporting")
