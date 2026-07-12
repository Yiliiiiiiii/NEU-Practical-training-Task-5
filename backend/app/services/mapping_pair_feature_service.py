import re
from difflib import SequenceMatcher
from typing import Any

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_features import MappingPairFeatures
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.field_descriptor_service import FieldDescriptorService


class MappingPairFeatureService:
    def __init__(self, descriptor_service: FieldDescriptorService | None = None) -> None:
        self.descriptor_service = descriptor_service or FieldDescriptorService()

    def build(
        self,
        candidate: FieldCandidate,
        target: TargetField,
        template: MappingTemplate,
        *,
        negative_pairs: list[dict[str, Any]] | None = None,
        uir: UIRDocument | None = None,
    ) -> MappingPairFeatures:
        reasons: list[str] = []
        risk_flags: list[str] = []
        target_descriptor = self.descriptor_service.target_descriptor(target, template)
        candidate_descriptor = self.descriptor_service.candidate_descriptor(candidate, uir)
        lexical_score = self._lexical_score(candidate, target, template)
        alias_score = self._alias_score(candidate, target, template, reasons)
        type_score = self._type_score(candidate.inferred_type, target.type)
        value_score = self._value_score(candidate.value_sample, target.type)
        path_score = self._path_score(candidate, target)
        context_score = self._context_score(
            candidate,
            has_context=bool(
                candidate_descriptor.section_title_path or candidate_descriptor.neighbor_labels
            ),
        )
        evidence_score = self._evidence_score(candidate, template)
        negative_score = self._negative_score(
            candidate,
            target,
            negative_pairs or [],
        )
        source_quality_score = self._source_quality_score(candidate)
        if negative_score >= 1.0:
            risk_flags.append("negative_pair_block")
        if type_score < 0.5:
            risk_flags.append("type_mismatch")
        if value_score < 0.5:
            risk_flags.append("value_shape_mismatch")
        if target_descriptor.required:
            reasons.append("required_target")

        scoring = template.scoring
        effective_source_quality = (source_quality_score + evidence_score) / 2.0
        final_score = (
            lexical_score * scoring.lexical_weight
            + alias_score * scoring.alias_weight
            + type_score * scoring.type_weight
            + value_score * scoring.value_shape_weight
            + path_score * scoring.path_weight
            + context_score * scoring.context_weight
            + effective_source_quality * scoring.source_quality_weight
            - negative_score
        )
        return MappingPairFeatures(
            source_candidate_id=candidate.candidate_id,
            source_path=candidate.source_path,
            source_name=candidate.source_name,
            target_field_id=target.field_id,
            target_name=target.name,
            lexical_score=round(lexical_score, 4),
            alias_score=round(alias_score, 4),
            type_score=round(type_score, 4),
            value_score=round(value_score, 4),
            path_score=round(path_score, 4),
            context_score=round(context_score, 4),
            evidence_score=round(evidence_score, 4),
            negative_score=round(negative_score, 4),
            source_quality_score=round(source_quality_score, 4),
            final_score=round(max(0.0, min(final_score, 1.0)), 4),
            reasons=reasons,
            risk_flags=sorted(set(risk_flags)),
        )

    def _lexical_score(
        self,
        candidate: FieldCandidate,
        target: TargetField,
        template: MappingTemplate,
    ) -> float:
        source_terms = [
            candidate.source_name,
            candidate.display_name or "",
        ]
        target_terms = [
            target.field_id,
            target.name,
            target.display_name,
            *target.aliases,
            *template.aliases.get(target.field_id, []),
        ]
        return max(
            (
                self._similarity(source, target_term)
                for source in source_terms
                for target_term in target_terms
                if source and target_term
            ),
            default=0.0,
        )

    def _alias_score(
        self,
        candidate: FieldCandidate,
        target: TargetField,
        template: MappingTemplate,
        reasons: list[str],
    ) -> float:
        aliases = {
            self._normalize(value)
            for value in [
                target.field_id,
                target.name,
                target.display_name,
                *target.aliases,
                *template.aliases.get(target.field_id, []),
            ]
            if value
        }
        candidate_names = {
            self._normalize(candidate.source_name),
            self._normalize(candidate.display_name or ""),
        }
        if aliases & candidate_names:
            reasons.append("alias_match")
            return 1.0
        if target.field_id in candidate.target_hints:
            reasons.append("target_hint_match")
            return 0.9
        return 0.0

    @staticmethod
    def _type_score(candidate_type: str, field_type: str) -> float:
        if candidate_type == field_type:
            return 1.0
        if field_type in {"string", "text"} and candidate_type in {
            "string",
            "text",
            "organization",
            "date",
        }:
            return 0.9
        if field_type.startswith("array") and candidate_type in {
            "array",
            "list",
            "list_like",
        }:
            return 1.0
        if field_type.startswith("array") and candidate_type in {"string", "text"}:
            return 0.6
        if field_type in {"date", "datetime"} and candidate_type in {
            "date",
            "datetime",
            "string",
        }:
            return 0.85
        if field_type == "number" and candidate_type in {"number", "integer"}:
            return 1.0
        return 0.4

    def _value_score(self, value: Any, field_type: str) -> float:
        if field_type == "date":
            return self._date_value_score(value)
        if field_type == "datetime":
            if isinstance(value, str) and re.search(
                r"\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}",
                value,
            ):
                return 1.0
            return 0.6 if self._date_value_score(value) >= 1.0 else 0.2
        if field_type == "number":
            if isinstance(value, int | float):
                return 1.0
            if isinstance(value, str) and re.search(r"\d[\d,]*(?:\.\d+)?", value):
                return 1.0
            return 0.2
        if field_type.startswith("array"):
            if isinstance(value, list):
                return 1.0
            if isinstance(value, str) and ("\n" in value or "；" in value or ";" in value):
                return 1.0
            return 0.4
        return 0.8 if value not in (None, "") else 0.2

    @staticmethod
    def _date_value_score(value: Any) -> float:
        if isinstance(value, str):
            if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value.strip()):
                return 1.0
            if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
                return 0.7
        return 0.2

    def _path_score(self, candidate: FieldCandidate, target: TargetField) -> float:
        normalized_path = self._normalize(candidate.source_path)
        normalized_target = self._normalize(target.field_id)
        if normalized_target and normalized_target in normalized_path:
            return 1.0
        if candidate.source_path.startswith("$.metadata."):
            return 0.8
        if candidate.source_blocks:
            return 0.7
        return 0.4

    @staticmethod
    def _context_score(candidate: FieldCandidate, *, has_context: bool = False) -> float:
        if has_context:
            return 1.0
        if candidate.source_blocks:
            return 0.9
        if candidate.source_path.startswith("$.metadata."):
            return 0.75
        return 0.5

    @staticmethod
    def _evidence_score(candidate: FieldCandidate, template: MappingTemplate) -> float:
        evidence_type = candidate.evidence_type
        if evidence_type in template.evidence_weights:
            return template.evidence_weights[evidence_type]
        if evidence_type and template.unknown_evidence_policy == "reject":
            raise ValueError(f"unknown mapping evidence type: {evidence_type}")
        return template.neutral_evidence_weight

    def _negative_score(
        self,
        candidate: FieldCandidate,
        target: TargetField,
        negative_pairs: list[dict[str, Any]],
    ) -> float:
        for negative in negative_pairs:
            if negative.get("target_field_id") != target.field_id:
                continue
            source_path = negative.get("source_path")
            if isinstance(source_path, str) and source_path == candidate.source_path:
                return 1.0
            pattern = negative.get("source_pattern")
            if isinstance(pattern, str):
                if re.search(pattern, candidate.source_name, flags=re.IGNORECASE):
                    return 1.0
                if re.search(pattern, candidate.source_path, flags=re.IGNORECASE):
                    return 1.0
        return 0.0

    @staticmethod
    def _source_quality_score(candidate: FieldCandidate) -> float:
        if candidate.source_path and candidate.source_blocks:
            return 1.0
        if candidate.source_path.startswith("$.metadata."):
            return 0.85
        if candidate.source_path:
            return 0.5
        return 0.0

    @staticmethod
    def _normalize(value: str) -> str:
        return CandidateService.normalize_name(value)

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        return SequenceMatcher(None, cls._normalize(left), cls._normalize(right)).ratio()
