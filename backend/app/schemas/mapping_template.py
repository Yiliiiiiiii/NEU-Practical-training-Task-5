from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.transform import TransformRule


class RegexRule(StrictBaseModel):
    target_field_id: str
    pattern: str
    group: int = 0


class MappingTemplate(StrictBaseModel):
    template_id: str
    schema_id: str
    name: str
    version: str
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    regex_rules: list[RegexRule] = Field(default_factory=list)
    transform_rules: list[TransformRule] = Field(default_factory=list)
    defaults: dict[str, object] = Field(default_factory=dict)
    enum_maps: dict[str, dict[str, str]] = Field(default_factory=dict)
