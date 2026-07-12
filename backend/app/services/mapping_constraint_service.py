from __future__ import annotations

from typing import Any

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingConstraintPolicy
from app.schemas.target_schema import TargetField


class MappingConstraintService:
    def policy(
        self, configured: MappingConstraintPolicy, options: dict[str, Any]
    ) -> MappingConstraintPolicy:
        override = options.get("constraints")
        if override is None:
            return configured
        return MappingConstraintPolicy.model_validate(override)

    @staticmethod
    def minimum_score(
        target: TargetField,
        policy: MappingConstraintPolicy,
        default: float,
    ) -> float:
        return policy.field_min_scores.get(target.field_id, default)

    @staticmethod
    def type_is_compatible(type_score: float, policy: MappingConstraintPolicy) -> bool:
        return type_score >= policy.min_type_score

    @staticmethod
    def source_reuse_allowed(
        candidate: FieldCandidate,
        target: TargetField,
        policy: MappingConstraintPolicy,
    ) -> bool:
        return any(
            rule.source_path == candidate.source_path and target.field_id in rule.target_field_ids
            for rule in policy.source_reuse_rules
        )

    @staticmethod
    def operation(
        candidate: FieldCandidate,
        target: TargetField,
        policy: MappingConstraintPolicy,
    ) -> str:
        for rule in policy.cardinality_rules:
            if (
                rule.target_field_id == target.field_id
                and candidate.source_path in rule.source_paths
            ):
                return rule.operation
        return "one_to_one"
