import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.llm_fallback_service import LLMFallbackService


class MappingService:
    REVIEW_CONFIDENCE = 0.62

    def __init__(self, llm_fallback_service: LLMFallbackService | None = None) -> None:
        self.llm_fallback_service = llm_fallback_service or LLMFallbackService()

    def map_fields(
        self,
        task_id: str,
        uir: UIRDocument,
        schema: TargetSchema,
        template: MappingTemplate,
        candidates: list[FieldCandidate],
        options: dict[str, Any] | None = None,
    ) -> MappingReport:
        options = options or {}
        mappings: list[dict[str, Any]] = []
        review_required: list[dict[str, Any]] = []
        used_source_paths: set[str] = set()
        strategy_counts: Counter[str] = Counter(
            {"exact": 0, "alias": 0, "regex": 0, "type": 0, "fuzzy": 0, "llm_fallback": 0}
        )

        for field in schema.fields:
            mapping = self._find_exact(task_id, field, candidates, used_source_paths)
            if mapping is None:
                mapping = self._find_alias(task_id, field, template, candidates, used_source_paths)
            if mapping is None:
                mapping = self._find_regex(task_id, field, template, uir)
            if mapping is None:
                mapping = self._find_type(task_id, field, candidates, used_source_paths)

            if mapping is not None:
                mappings.append(mapping.model_dump(mode="json"))
                used_source_paths.add(mapping.source_field.source_path)
                strategy_counts[mapping.method] += 1
                continue

            review_item = self._find_fuzzy(task_id, field, candidates, used_source_paths)
            if review_item is None and options.get("enable_llm_fallback"):
                review_item = self.llm_fallback_service.suggest_mapping(
                    task_id=task_id,
                    field=field,
                    candidates=candidates,
                    used_source_paths=used_source_paths,
                    badcases=options.get("badcases", []),
                )

            if review_item is not None:
                review_data = review_item.model_dump(mode="json")
                review_required.append(review_data)
                strategy_counts[review_item.method] += 1

        mapped_targets = {mapping["target_field_id"] for mapping in mappings}
        unmapped = [
            {
                "target_field_id": field.field_id,
                "target_field_name": field.name,
                "required": field.required,
                "reason": "required field was not confirmed by deterministic mapping",
            }
            for field in schema.fields
            if field.required and field.field_id not in mapped_targets
        ]
        confidences = [mapping["confidence"] for mapping in mappings]

        return MappingReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            summary={
                "template_id": template.template_id,
                "total_candidates": len(candidates),
                "target_fields": len(schema.fields),
                "mapped_fields": len(mappings),
                "review_required": len(review_required),
                "unmapped_required_fields": len(unmapped),
                "average_confidence": round(sum(confidences) / len(confidences), 4)
                if confidences
                else 0.0,
                "strategy_counts": dict(strategy_counts),
                "methods": {key: value for key, value in strategy_counts.items() if value},
            },
            mappings=mappings,
            unmapped=unmapped,
            review_required_items=review_required,
        )

    def _find_exact(
        self,
        task_id: str,
        field: TargetField,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
    ) -> FieldMapping | None:
        target_names = {
            self.normalize_name(field.field_id),
            self.normalize_name(field.name),
        }
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            if self.normalize_name(candidate.source_name) in target_names:
                return self._mapping(task_id, candidate, field, "exact", 1.0, False)
        return None

    def _find_alias(
        self,
        task_id: str,
        field: TargetField,
        template: MappingTemplate,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
    ) -> FieldMapping | None:
        aliases = set(template.aliases.get(field.field_id, []))
        aliases.update(field.aliases)
        aliases.add(field.display_name)
        normalized_aliases = {self.normalize_name(alias) for alias in aliases}
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            if self.normalize_name(candidate.source_name) in normalized_aliases:
                return self._mapping(
                    task_id,
                    candidate,
                    field,
                    "alias",
                    0.96,
                    False,
                    evidence=[f"alias matched target {field.field_id}"],
                )
        return None

    def _find_regex(
        self,
        task_id: str,
        field: TargetField,
        template: MappingTemplate,
        uir: UIRDocument,
    ) -> FieldMapping | None:
        rules = [rule for rule in template.regex_rules if rule.target_field_id == field.field_id]
        if not rules:
            return None
        text_by_block = {
            block.block_id: block.text or ""
            for block in uir.blocks
            if block.text
        }
        full_text = "\n".join(text_by_block.values())
        for rule in rules:
            match = re.search(rule.pattern, full_text)
            if not match:
                continue
            value = match.group(rule.group)
            source_blocks = [
                block_id for block_id, block_text in text_by_block.items() if value in block_text
            ]
            candidate = FieldCandidate(
                candidate_id=f"cand_{task_id}_regex_{field.field_id}",
                task_id=task_id,
                doc_id=uir.doc_id,
                source_path=f"$.blocks.regex.{field.field_id}",
                source_name=field.field_id,
                display_name=field.display_name,
                value_sample=value,
                inferred_type=CandidateService.infer_type(value),
                source_blocks=source_blocks,
                confidence=0.9,
                evidence=[f"regex matched {rule.pattern}"],
            )
            return self._mapping(
                task_id,
                candidate,
                field,
                "regex",
                0.92,
                False,
                evidence=[f"regex rule matched target {field.field_id}"],
            )
        return None

    def _find_type(
        self,
        task_id: str,
        field: TargetField,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
    ) -> FieldMapping | None:
        if field.field_id != "content" or field.type != "text":
            return None
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            if candidate.inferred_type in {"string", "text"} and candidate.source_blocks:
                return self._mapping(
                    task_id,
                    candidate,
                    field,
                    "type",
                    0.74,
                    False,
                    evidence=["text block candidate matched content field by type"],
                )
        return None

    def _find_fuzzy(
        self,
        task_id: str,
        field: TargetField,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
    ) -> FieldMapping | None:
        best_candidate: FieldCandidate | None = None
        best_score = 0.0
        field_terms = [field.field_id, field.name, field.display_name, *field.aliases]
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            score = max(
                self._similarity(candidate.source_name, term)
                for term in field_terms
                if term
            )
            score = max(score, self._semantic_hint_score(candidate.source_name, field))
            if score > best_score:
                best_candidate = candidate
                best_score = score

        if best_candidate is None or best_score < 0.45:
            return None
        return self._mapping(
            task_id,
            best_candidate,
            field,
            "fuzzy",
            self.REVIEW_CONFIDENCE,
            True,
            evidence=[f"fuzzy score {best_score:.2f} requires review"],
        )

    def _mapping(
        self,
        task_id: str,
        candidate: FieldCandidate,
        field: TargetField,
        method: str,
        confidence: float,
        need_review: bool,
        evidence: list[str] | None = None,
    ) -> FieldMapping:
        status = "review_required" if need_review else "confirmed"
        return FieldMapping(
            mapping_id=f"map_{task_id}_{field.field_id}_{method}",
            task_id=task_id,
            candidate_id=candidate.candidate_id,
            source_field={
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            target_field_id=field.field_id,
            target_field_name=field.name,
            method=method,
            confidence=confidence,
            status=status,
            need_review=need_review,
            value_sample=candidate.value_sample,
            source_blocks=candidate.source_blocks,
            evidence=evidence or [f"{method} mapping to {field.field_id}"],
        )

    @staticmethod
    def normalize_name(value: str) -> str:
        return CandidateService.normalize_name(value)

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        return SequenceMatcher(
            None,
            CandidateService.normalize_name(left),
            CandidateService.normalize_name(right),
        ).ratio()

    @staticmethod
    def _semantic_hint_score(source_name: str, field: TargetField) -> float:
        source = source_name.lower()
        target = field.field_id
        if target in {"title", "contract_title", "meeting_title"} and any(
            token in source for token in ("名称", "题名", "标题", "主题")
        ):
            return 0.7
        if target in {"issuer", "party_a", "party_b", "organizer", "source"} and any(
            token in source for token in ("主体", "单位", "机构", "机关", "方", "召集人", "来源")
        ):
            return 0.65
        if target in {"publish_date", "sign_date", "meeting_date", "created_date"} and any(
            token in source for token in ("日期", "时间", "成文", "产生")
        ):
            return 0.65
        if target in {"amount", "currency"} and any(
            token in source for token in ("金额", "费用", "人民币")
        ):
            return 0.65
        if target in {"status", "category", "tags", "keywords", "attendees"}:
            return 0.5
        return 0.0
