import hashlib
import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from app.schemas.package import Manifest, ManifestFile

PAYLOAD_REQUIRED = {
    "content.json": True,
    "content.md": True,
    "chunks.json": True,
    "metadata.json": True,
    "config_snapshot.json": True,
    "mapping_report.json": True,
    "validation_report.json": True,
    "consistency_report.json": True,
    "trace.json": True,
}

PAYLOAD_ROLES = {
    "content.json": "content",
    "content.md": "content",
    "chunks.json": "content",
    "metadata.json": "metadata",
    "config_snapshot.json": "config",
    "mapping_report.json": "report",
    "validation_report.json": "report",
    "consistency_report.json": "report",
    "trace.json": "trace",
    "manifest.json": "manifest",
}

EXCLUDE_FROM_MANIFEST = {"manifest.json"}


def generate_manifest(
    task_id: str,
    doc_id: str,
    package_id: str,
    staging_dir: Path,
    package_version: str = "1.0.0",
) -> Manifest:
    files: list[ManifestFile] = []

    for path in sorted(staging_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(staging_dir).as_posix()
        if rel in EXCLUDE_FROM_MANIFEST:
            continue

        raw = path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        media_type = mimetypes.guess_type(rel)[0] or "application/octet-stream"
        required = PAYLOAD_REQUIRED.get(rel, False)
        role = PAYLOAD_ROLES.get(rel, "asset")

        files.append(ManifestFile(
            path=rel,
            required=required,
            media_type=media_type,
            sha256=sha256,
            bytes=len(raw),
            role=role,
        ))

    return Manifest(
        manifest_version="1.0",
        package_id=package_id,
        package_version=package_version,
        task_id=task_id,
        doc_id=doc_id,
        created_at=datetime.now(UTC).isoformat(),
        files=files,
        generator={"name": "schemapack-agent", "version": package_version},
    )
