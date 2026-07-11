from pydantic import Field

from app.schemas.common import StrictBaseModel


class ManifestFile(StrictBaseModel):
    path: str
    required: bool
    media_type: str
    sha256: str
    bytes: int
    role: str | None = None


class Manifest(StrictBaseModel):
    manifest_version: str
    package_id: str
    package_version: str
    task_id: str
    doc_id: str
    created_at: str
    files: list[ManifestFile] = Field(default_factory=list)
    generator: dict[str, str]


class OutputPackageMetadata(StrictBaseModel):
    package_id: str
    task_id: str
    doc_id: str
    schema_id: str
    template_id: str
    package_version: str
    zip_path: str | None
    status: str
    sha256: str | None = None
    manifest_sha256: str | None = None
    verifier_report_sha256: str | None = None
    zip_sha256: str | None = None
    created_at: str
