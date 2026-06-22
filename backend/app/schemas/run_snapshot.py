from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class ExecutionSnapshot(StrictBaseModel):
    snapshot_version: str
    task_id: str
    parent_task_id: str | None = None
    input_hash: str
    schema_ref: dict[str, str]
    template_ref: dict[str, str]
    options: dict[str, Any] = Field(default_factory=dict)
    engine_version: str
    build_commit: str | None = None
    prompt_version: str | None = None
    model: dict[str, Any] = Field(default_factory=dict)
    confirmed_mapping_ids: list[str] = Field(default_factory=list)
    created_at: str
