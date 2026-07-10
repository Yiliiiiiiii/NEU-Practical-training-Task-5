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
    summary_consistent: bool
    metadata_consistent: bool
