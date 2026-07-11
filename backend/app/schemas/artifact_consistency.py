from typing import Any, Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


class ArtifactConsistencyCheck(StrictBaseModel):
    check_name: str
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ArtifactConsistencyIssue(StrictBaseModel):
    stage: Literal["artifact_consistency"] = "artifact_consistency"
    path: str
    error_code: str
    message: str


class ArtifactConsistencyReport(StrictBaseModel):
    passed: bool
    checks: list[ArtifactConsistencyCheck] = Field(default_factory=list)
    errors: list[ArtifactConsistencyIssue] = Field(default_factory=list)
    warnings: list[ArtifactConsistencyIssue] = Field(default_factory=list)
    field_coverage: float = Field(ge=0.0, le=1.0)
    block_coverage: float = Field(ge=0.0, le=1.0)
    chunk_source_coverage: float = Field(ge=0.0, le=1.0)
    chunk_source_validity: float | None = Field(default=None, ge=0.0, le=1.0)
    canonical_block_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    nonempty_block_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    protected_block_integrity: float | None = Field(default=None, ge=0.0, le=1.0)
    duplicate_content_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    unexplained_chunk_text_count: int | None = Field(default=None, ge=0)
    unknown_source_count: int | None = Field(default=None, ge=0)
    artifact_input_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_input_fingerprint: str | None = None
    summary_consistent: bool
    metadata_consistent: bool
