from typing import Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel


class OutputProfile(StrictBaseModel):
    profile_id: str
    format: Literal["json", "jsonl", "csv"]
    source_path: str
    file_name: str
    field_order: list[str] = Field(default_factory=list)
