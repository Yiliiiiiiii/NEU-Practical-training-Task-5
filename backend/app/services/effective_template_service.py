import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import KnowledgePackItemRecord, KnowledgePackRecord
from app.schemas.mapping_template import MappingTemplate, RegexRule
from app.schemas.transform import TransformRule


class EffectiveTemplateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(self, template: MappingTemplate) -> tuple[MappingTemplate, list[str]]:
        data = template.model_dump(mode="json")
        pack_ids: list[str] = []

        packs = (
            self.db.query(KnowledgePackRecord)
            .filter(KnowledgePackRecord.status == "active")
            .order_by(KnowledgePackRecord.created_at.asc(), KnowledgePackRecord.pack_id.asc())
            .all()
        )
        for pack in packs:
            scope = self._load_json_object(pack.scope_json)
            if not self._scope_matches(scope, template):
                continue

            pack_ids.append(pack.pack_id)
            items = (
                self.db.query(KnowledgePackItemRecord)
                .filter(KnowledgePackItemRecord.pack_id == pack.pack_id)
                .order_by(
                    KnowledgePackItemRecord.created_at.asc(),
                    KnowledgePackItemRecord.item_id.asc(),
                )
                .all()
            )
            for item in items:
                payload = self._load_json_object(item.payload_json)
                if item.item_type == "alias_candidate" and item.target_field_id:
                    new_aliases = payload.get("aliases")
                    if not isinstance(new_aliases, list):
                        continue
                    aliases = data.setdefault("aliases", {}).setdefault(item.target_field_id, [])
                    for alias in new_aliases:
                        if alias not in aliases:
                            aliases.append(alias)
                elif item.item_type == "regex_candidate":
                    data.setdefault("regex_rules", []).append(payload)
                elif item.item_type == "enum_map_candidate" and item.target_field_id:
                    enum_map = data.setdefault("enum_maps", {}).setdefault(
                        item.target_field_id,
                        {},
                    )
                    enum_map.update(payload.get("map", {}))
                elif item.item_type == "default_candidate" and item.target_field_id:
                    data.setdefault("defaults", {})[item.target_field_id] = payload.get("value")
                elif item.item_type == "transform_candidate":
                    data.setdefault("transform_rules", []).append(payload)

        return MappingTemplate(
            **{
                **data,
                "regex_rules": [
                    RegexRule.model_validate(rule)
                    for rule in data.get("regex_rules", [])
                ],
                "transform_rules": [
                    TransformRule.model_validate(rule)
                    for rule in data.get("transform_rules", [])
                ],
            }
        ), pack_ids

    @staticmethod
    def _scope_matches(scope: dict[str, Any], template: MappingTemplate) -> bool:
        schema_id = scope.get("schema_id")
        template_id = scope.get("template_id")
        if template_id and template_id != template.template_id:
            return False
        if schema_id and schema_id != template.schema_id:
            return False
        return bool(schema_id or template_id)

    @staticmethod
    def _load_json_object(raw_json: str | None) -> dict[str, Any]:
        value = json.loads(raw_json or "{}")
        if isinstance(value, dict):
            return value
        return {}
