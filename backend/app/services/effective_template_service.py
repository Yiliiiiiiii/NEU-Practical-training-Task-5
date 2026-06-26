from dataclasses import dataclass

from app.schemas.mapping_template import MappingTemplate
from app.services.knowledge_service import KnowledgePack


@dataclass(frozen=True)
class EffectiveTemplateResult:
    template: MappingTemplate
    applied_pack_ids: list[str]


class EffectiveTemplateService:
    def resolve(
        self,
        base_template: MappingTemplate,
        packs: list[KnowledgePack] | None = None,
    ) -> EffectiveTemplateResult:
        data = base_template.model_dump(mode="json")
        applied_pack_ids: list[str] = []
        for pack in packs or []:
            if pack.status != "active":
                continue
            if pack.schema_id != base_template.schema_id:
                continue
            if pack.template_id != base_template.template_id:
                continue
            for target_field, aliases in pack.aliases.items():
                data.setdefault("aliases", {}).setdefault(target_field, [])
                for alias in aliases:
                    if alias not in data["aliases"][target_field]:
                        data["aliases"][target_field].append(alias)
            applied_pack_ids.append(pack.pack_id)

        return EffectiveTemplateResult(
            template=MappingTemplate.model_validate(data),
            applied_pack_ids=applied_pack_ids,
        )
