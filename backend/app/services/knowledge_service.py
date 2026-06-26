from dataclasses import dataclass, field
from typing import Any

from app.schemas.reports import MappingReport
from app.schemas.review import ReviewRecord


@dataclass(frozen=True)
class KnowledgeCandidate:
    candidate_id: str
    schema_id: str
    template_id: str
    source_field: str
    target_field_id: str
    support_count: int = 1
    status: str = "candidate"


@dataclass(frozen=True)
class KnowledgePack:
    pack_id: str
    schema_id: str
    template_id: str
    aliases: dict[str, list[str]] = field(default_factory=dict)
    status: str = "draft"
    candidate_ids: list[str] = field(default_factory=list)


class KnowledgeService:
    def derive_candidates(
        self,
        review_records: list[ReviewRecord],
        mapping_report: MappingReport,
        schema_id: str,
        template_id: str,
        badcases: list[dict[str, Any]] | None = None,
    ) -> list[KnowledgeCandidate]:
        review_items = {
            item.get("mapping_id"): item
            for item in mapping_report.review_required_items
            if item.get("mapping_id")
        }
        approved = [
            record for record in review_records if record.decision == "approved"
        ]
        candidates: dict[tuple[str, str], KnowledgeCandidate] = {}
        for record in approved:
            item = review_items.get(record.mapping_id)
            if item is None:
                continue
            source_name = self._source_name(item)
            target_field_id = record.new_target_field_id or item.get("target_field_id")
            if not isinstance(source_name, str) or not isinstance(target_field_id, str):
                continue
            if self._is_badcase_forbidden(source_name, target_field_id, badcases or []):
                continue

            key = (source_name, target_field_id)
            existing = candidates.get(key)
            if existing is None:
                candidates[key] = KnowledgeCandidate(
                    candidate_id=f"kc_{schema_id}_{template_id}_{len(candidates) + 1}",
                    schema_id=schema_id,
                    template_id=template_id,
                    source_field=source_name,
                    target_field_id=target_field_id,
                )
            else:
                candidates[key] = KnowledgeCandidate(
                    candidate_id=existing.candidate_id,
                    schema_id=existing.schema_id,
                    template_id=existing.template_id,
                    source_field=existing.source_field,
                    target_field_id=existing.target_field_id,
                    support_count=existing.support_count + 1,
                    status=existing.status,
                )
        return sorted(candidates.values(), key=lambda item: item.candidate_id)

    def create_draft_pack(
        self,
        candidates: list[KnowledgeCandidate],
        schema_id: str,
        template_id: str,
    ) -> KnowledgePack:
        aliases: dict[str, list[str]] = {}
        for candidate in candidates:
            if candidate.schema_id != schema_id or candidate.template_id != template_id:
                continue
            aliases.setdefault(candidate.target_field_id, [])
            if candidate.source_field not in aliases[candidate.target_field_id]:
                aliases[candidate.target_field_id].append(candidate.source_field)

        normalized_aliases = {
            target_field: sorted(values)
            for target_field, values in sorted(aliases.items())
        }
        return KnowledgePack(
            pack_id=f"kp_{schema_id}_{template_id}_draft",
            schema_id=schema_id,
            template_id=template_id,
            aliases=normalized_aliases,
            status="draft",
            candidate_ids=sorted({candidate.candidate_id for candidate in candidates}),
        )

    def derive_gold_candidates(
        self,
        gold_cases: list[dict[str, Any]],
        badcases: list[dict[str, Any]] | None = None,
    ) -> list[KnowledgeCandidate]:
        candidates: list[KnowledgeCandidate] = []
        seen: set[tuple[str, str, str, str]] = set()
        for case in gold_cases:
            if case.get("expected_behavior") != "review_required_before_pack_auto_after_pack":
                continue
            source_field = case.get("source_field")
            target_field_id = case.get("expected_target_field")
            schema_id = case.get("schema_id")
            template_id = case.get("template_id")
            if not all(
                isinstance(value, str)
                for value in (source_field, target_field_id, schema_id, template_id)
            ):
                continue
            if self._is_badcase_forbidden(source_field, target_field_id, badcases or []):
                continue
            key = (schema_id, template_id, source_field, target_field_id)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                KnowledgeCandidate(
                    candidate_id=f"kc_gold_{len(candidates) + 1}",
                    schema_id=schema_id,
                    template_id=template_id,
                    source_field=source_field,
                    target_field_id=target_field_id,
                )
            )
        return candidates

    def activate_pack(self, pack: KnowledgePack) -> KnowledgePack:
        return KnowledgePack(
            pack_id=pack.pack_id.replace("_draft", "_active"),
            schema_id=pack.schema_id,
            template_id=pack.template_id,
            aliases=pack.aliases,
            status="active",
            candidate_ids=pack.candidate_ids,
        )

    @staticmethod
    def active_packs(packs: list[KnowledgePack]) -> list[KnowledgePack]:
        return [pack for pack in packs if pack.status == "active"]

    @staticmethod
    def _source_name(item: dict[str, Any]) -> str | None:
        source_field = item.get("source_field")
        if not isinstance(source_field, dict):
            return None
        source_name = source_field.get("source_name")
        return source_name if isinstance(source_name, str) else None

    @staticmethod
    def _is_badcase_forbidden(
        source_name: str,
        target_field_id: str,
        badcases: list[dict[str, Any]],
    ) -> bool:
        for badcase in badcases:
            if badcase.get("source_field") != source_name:
                continue
            forbidden = badcase.get("forbidden_target_fields", [])
            if isinstance(forbidden, list) and target_field_id in forbidden:
                return True
        return False
