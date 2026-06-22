from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import StrictBaseModel


class TransformRule(StrictBaseModel):
    rule_id: str
    operation: str
    source_field: str | None = None
    source_fields: list[str] = Field(default_factory=list)
    target_field_id: str | None = None
    target_fields: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    on_error: str = "record_and_continue"

    @model_validator(mode="after")
    def must_have_target(self) -> "TransformRule":
        if self.target_field_id is None and not self.target_fields:
            raise ValueError("transform rule must define target_field_id or target_fields")
        return self
