from __future__ import annotations

import re
from typing import Any

from app.schemas.mapping import FieldCandidate, MappingEvidence
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.mapping_pair_feature_service import MappingPairFeatureService
from app.services.mapping_service import MappingService


class MappingRepairService:
    DEFAULT_REVIEW_THRESHOLD = 0.62
    DEFAULT_MAX_REPAIR_ROUNDS = 2

    def __init__(
        self,
        pair_feature_service: MappingPairFeatureService | None = None,
    ) -> None:
        self.pair_feature_service = pair_feature_service or MappingPairFeatureService()
        self.mapping_service = MappingService()

    def repair(
        self,
        *,
        task_id: str,
        uir: UIRDocument,
        schema: TargetSchema,
        template: MappingTemplate,
        candidates: list[FieldCandidate],
        mapping_report: MappingReport,
        options: dict[str, Any] | None = None,
    ) -> tuple[MappingReport, dict[str, Any]]:
        options = options or {}
        enabled = bool(options.get("enable_mapping_repair"))
        report: dict[str, Any] = {
            "enabled": enabled,
            "rounds": 0,
            "attempted_fields": [],
            "repaired_fields": [],
            "unrepaired_fields": [],
            "blocked_candidates": [],
        }
        if not enabled:
            return mapping_report, report

        negative_pairs = options.get("negative_pairs", [])
        negative_pairs = negative_pairs if isinstance(negative_pairs, list) else []
        review_threshold = float(options.get("review_threshold", self.DEFAULT_REVIEW_THRESHOLD))
        max_rounds = int(options.get("max_repair_rounds", self.DEFAULT_MAX_REPAIR_ROUNDS))
        report["rounds"] = min(max_rounds, 1)

        mappings = list(mapping_report.mappings)
        review_required = list(mapping_report.review_required_items)
        used_sources = {
            item.get("source_path")
            for item in [*mappings, *review_required]
            if isinstance(item.get("source_path"), str)
        }
        unresolved = {
            str(item.get("target_field_id"))
            for item in mapping_report.unmapped
            if item.get("required") and item.get("target_field_id")
        }
        fields_by_id = {field.field_id: field for field in schema.fields}

        for field_id in sorted(unresolved):
            target = fields_by_id.get(field_id)
            if target is None:
                continue
            report["attempted_fields"].append(field_id)
            ranked = []
            for candidate in candidates:
                if candidate.source_path in used_sources:
                    continue
                features = self.pair_feature_service.build(
                    candidate,
                    target,
                    template,
                    negative_pairs=negative_pairs,
                )
                negative_reason = self._negative_reason(candidate, target, negative_pairs)
                if negative_reason is not None:
                    report["blocked_candidates"].append(
                        {
                            "target_field_id": target.field_id,
                            "candidate_id": candidate.candidate_id,
                            "reason": negative_reason,
                        }
                    )
                    continue
                ranked.append((features.final_score, candidate, features))
            ranked.sort(
                key=lambda item: (
                    -item[0],
                    -float(item[1].confidence_hint or item[1].confidence),
                    item[1].source_path,
                )
            )
            if not ranked or ranked[0][0] < review_threshold:
                report["unrepaired_fields"].append(field_id)
                continue
            score, candidate, features = ranked[0]
            mappings.append(
                self._repair_mapping(task_id, candidate, target, score, features)
            )
            used_sources.add(candidate.source_path)
            report["repaired_fields"].append(field_id)

        repaired_fields = set(report["repaired_fields"])
        unmapped = [
            item
            for item in mapping_report.unmapped
            if item.get("target_field_id") not in repaired_fields
        ]
        summary = dict(mapping_report.summary)
        summary["mapping_repair_enabled"] = True
        summary["mapping_repair_attempted_count"] = len(report["attempted_fields"])
        summary["mapping_repair_repaired_count"] = len(report["repaired_fields"])
        summary["mapped_count"] = len(mappings)
        summary["accepted_count"] = len(mappings)
        summary["review_required_count"] = len(review_required)
        summary["failed_count"] = len(unmapped)
        summary["required_unmapped_count"] = len(
            [item for item in unmapped if item.get("required")]
        )
        summary["unmapped_required_fields"] = summary["required_unmapped_count"]
        return (
            MappingReport(
                task_id=mapping_report.task_id,
                schema_id=mapping_report.schema_id,
                summary=summary,
                mappings=mappings,
                review_required_items=review_required,
                unmapped=unmapped,
            ),
            report,
        )

    def _repair_mapping(
        self,
        task_id: str,
        candidate: FieldCandidate,
        target: TargetField,
        score: float,
        features: Any,
    ) -> dict[str, Any]:
        mapping = self.mapping_service._mapping(
            task_id=task_id,
            candidate=candidate,
            field=target,
            method="mapping_repair",
            confidence=score,
            need_review=False,
            evidence=[
                MappingEvidence(
                    type="mapping_repair",
                    message=f"deterministic repair selected score {score:.3f}",
                    weight=score,
                )
            ],
            ranking_trace={
                "final_score": features.final_score,
                "lexical_score": features.lexical_score,
                "alias_score": features.alias_score,
                "type_score": features.type_score,
                "value_score": features.value_score,
                "negative_score": features.negative_score,
            },
        )
        return mapping.model_dump(mode="json")

    @staticmethod
    def _negative_reason(
        candidate: FieldCandidate,
        target: TargetField,
        negative_pairs: list[dict[str, Any]],
    ) -> str | None:
        for item in negative_pairs:
            if item.get("target_field_id") != target.field_id:
                continue
            pattern = item.get("source_pattern")
            if not isinstance(pattern, str):
                continue
            if re.search(pattern, candidate.source_name, flags=re.IGNORECASE) or re.search(
                pattern,
                candidate.source_path,
                flags=re.IGNORECASE,
            ):
                return str(item.get("reason") or "configured_negative_pair")
        return None
