from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.common import StrictBaseModel


class TargetFieldDescriptor(StrictBaseModel):
    field_id: str
    name: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    type: str
    required: bool
    enum_values: list[Any] = Field(default_factory=list)
    format_constraints: dict[str, Any] = Field(default_factory=dict)
    parent_path: str | None = None


class CandidateFieldDescriptor(StrictBaseModel):
    source_name: str
    display_name: str | None = None
    source_path: str
    inferred_type: str
    value_shape: str
    section_title_path: list[str] = Field(default_factory=list)
    block_type: str | None = None
    neighbor_labels: list[str] = Field(default_factory=list)
    source_evidence_type: str | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
