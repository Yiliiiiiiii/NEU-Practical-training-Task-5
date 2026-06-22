import re
from difflib import SequenceMatcher

from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.utils.ids import new_id


class MappingEngine:
    def map_fields(
        self,
        task_id: str,
        candidates: list[FieldCandidate],
        target_schema: TargetSchema,
        template: MappingTemplate,
        review_threshold: float,
    ) -> list[FieldMapping]:
        mappings: list[FieldMapping] = []
        used_candidates: set[str] = set()
        for target in target_schema.fields:
            scored = [
                self._score(candidate, target, template)
                for candidate in candidates
                if candidate.candidate_id not in used_candidates
            ]
            scored = [item for item in scored if item is not None]
            if not scored:
                continue

            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            _priority, confidence, method, candidate, evidence = scored[0]
            used_candidates.add(candidate.candidate_id)
            need_review = confidence < review_threshold
            mappings.append(
                FieldMapping(
                    mapping_id=new_id("map"),
                    task_id=task_id,
                    candidate_id=candidate.candidate_id,
                    source_field={
                        "source_path": candidate.source_path,
                        "source_name": candidate.source_name,
                    },
                    target_field_id=target.field_id,
                    target_field_name=target.name,
                    method=method,
                    confidence=confidence,
                    status="review_required" if need_review else "confirmed",
                    need_review=need_review,
                    evidence=evidence,
                )
            )
        return mappings

    def _score(
        self,
        candidate: FieldCandidate,
        target: TargetField,
        template: MappingTemplate,
    ) -> tuple[int, float, str, FieldCandidate, list[str]] | None:
        source = self._norm(candidate.source_name)
        target_names = {self._norm(target.field_id), self._norm(target.name)}
        if source in target_names:
            return 6, 1.0, "exact_match", candidate, ["source_name equals target name"]

        aliases = {
            self._norm(alias)
            for alias in [*template.aliases.get(target.field_id, []), *target.aliases]
        }
        if source in aliases:
            return 5, 0.95, "alias_match", candidate, ["source_name matched aliases"]

        for rule in template.regex_rules:
            if rule.target_field_id != target.field_id:
                continue
            match = re.search(rule.pattern, str(candidate.value_sample or ""))
            if match:
                extracted_value = match.group(rule.group)
                return 4, 0.9, "regex_match", candidate, [
                    "candidate value matched regex pattern",
                    extracted_value,
                ]

        if self._types_compatible(
            candidate.inferred_type,
            target.type,
        ) and not self._uses_default_value(target.field_id, template):
            unique_compatible_targets = self._compatible_target_count(candidate, template, target)
            if unique_compatible_targets == 1:
                return 3, 0.8, "type_match", candidate, ["candidate type uniquely matched"]

        fuzzy_score = self._best_fuzzy(source, target, aliases)
        if fuzzy_score >= 0.62:
            return 2, round(0.6 + fuzzy_score * 0.2, 3), "fuzzy_match", candidate, [
                "source_name similar to target aliases"
            ]
        return None

    @staticmethod
    def _norm(value: str) -> str:
        return value.strip().lower().replace("_", "").replace("-", "")

    @staticmethod
    def _types_compatible(candidate_type: str, target_type: str) -> bool:
        if candidate_type == target_type:
            return True
        return candidate_type == "integer" and target_type in {"int", "integer", "number"}

    @staticmethod
    def _compatible_target_count(
        candidate: FieldCandidate,
        template: MappingTemplate,
        current_target: TargetField,
    ) -> int:
        explicit_targets = set(template.aliases) | set(template.enum_maps)
        explicit_targets.update(rule.target_field_id for rule in template.regex_rules)
        explicit_targets.update(
            rule.target_field_id for rule in template.transform_rules if rule.target_field_id
        )
        if current_target.field_id in explicit_targets:
            return 1
        return 2 if candidate.inferred_type == "string" else 1

    @staticmethod
    def _uses_default_value(target_field_id: str, template: MappingTemplate) -> bool:
        if target_field_id in template.defaults:
            return True
        return any(
            rule.target_field_id == target_field_id and rule.operation == "default"
            for rule in template.transform_rules
        )

    @staticmethod
    def _best_fuzzy(source: str, target: TargetField, aliases: set[str]) -> float:
        choices = aliases | {
            MappingEngine._norm(target.field_id),
            MappingEngine._norm(target.name),
            MappingEngine._norm(target.display_name),
        }
        return max(SequenceMatcher(None, source, choice).ratio() for choice in choices)
