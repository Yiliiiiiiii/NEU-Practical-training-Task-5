import json
import re
from pathlib import Path

from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.services.candidate_service import CandidateService

DEFAULT_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[3] / "examples" / "production_like" / "mapping_templates"
)


class TemplateService:
    def __init__(self, templates_dir: str | Path = DEFAULT_TEMPLATE_DIR) -> None:
        self.templates_dir = Path(templates_dir)

    def list_templates(self) -> list[MappingTemplate]:
        templates = [self._load_template_file(path) for path in self._template_paths()]
        return sorted(templates, key=lambda template: (template.template_id, template.version))

    def load_template(self, template_id: str, version: str | None = None) -> MappingTemplate:
        for path in self._template_paths():
            template = self._load_template_file(path)
            if template.template_id == template_id and (
                version is None or template.version == version
            ):
                return template
        version_text = f" version {version}" if version is not None else ""
        raise LookupError(f"template {template_id}{version_text} not found")

    def validate_template(
        self,
        template: MappingTemplate,
        schema: TargetSchema,
    ) -> MappingTemplate:
        if template.schema_id != schema.schema_id:
            raise ValueError(
                f"template schema_id {template.schema_id} does not match schema {schema.schema_id}"
            )

        target_fields = {field.field_id for field in schema.fields}
        for target_field in template.aliases:
            if target_field not in target_fields:
                raise ValueError(f"unknown alias target: {target_field}")

        for rule in template.regex_rules:
            if rule.target_field_id not in target_fields:
                raise ValueError(f"unknown regex target: {rule.target_field_id}")
            try:
                re.compile(rule.pattern)
            except re.error as exc:
                raise ValueError(f"invalid regex rule for {rule.target_field_id}: {exc}") from exc

        for target_field in template.enum_maps:
            if target_field not in target_fields:
                raise ValueError(f"unknown enum_map target: {target_field}")

        for target_field in template.defaults:
            if target_field not in target_fields:
                raise ValueError(f"unknown default target: {target_field}")

        for rule in template.transform_rules:
            if rule.target_field_id is not None and rule.target_field_id not in target_fields:
                raise ValueError(f"unknown transform target: {rule.target_field_id}")
            for target_field in rule.target_fields:
                if target_field not in target_fields:
                    raise ValueError(f"unknown transform target: {target_field}")

        alias_owners: dict[str, set[str]] = {}
        for field in schema.fields:
            aliases = set(template.aliases.get(field.field_id, []))
            aliases.update(field.aliases)
            aliases.add(field.display_name)
            for alias in aliases:
                normalized_alias = CandidateService.normalize_name(alias)
                alias_owners.setdefault(normalized_alias, set()).add(field.field_id)
        collisions = {
            alias: sorted(owners)
            for alias, owners in alias_owners.items()
            if len(owners) > 1
        }
        if collisions:
            details = ", ".join(
                f"{alias}: {owners}" for alias, owners in sorted(collisions.items())
            )
            raise ValueError(f"effective alias collision across targets: {details}")

        return template

    def _template_paths(self) -> list[Path]:
        return sorted(self.templates_dir.glob("*.json"))

    @staticmethod
    def _load_template_file(path: Path) -> MappingTemplate:
        return MappingTemplate.model_validate(json.loads(path.read_text(encoding="utf-8")))
