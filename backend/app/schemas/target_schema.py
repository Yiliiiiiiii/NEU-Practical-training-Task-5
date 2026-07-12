from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import StrictBaseModel


class TargetField(StrictBaseModel):
    field_id: str
    name: str
    display_name: str
    type: str
    required: bool = False
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    parent_path: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class TargetSchema(StrictBaseModel):
    schema_id: str
    name: str
    version: str
    description: str | None = None
    fields: list[TargetField]
    json_schema: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def fields_must_not_be_empty(cls, value: list[TargetField]) -> list[TargetField]:
        if not value:
            raise ValueError("target schema must contain at least one field")
        return value
