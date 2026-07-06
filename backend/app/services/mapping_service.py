import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from app.schemas.mapping import FieldCandidate, FieldMapping, MappingEvidence
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.llm_fallback_service import LLMFallbackService


class MappingService:
    REVIEW_CONFIDENCE = 0.62
    MIN_FUZZY_REVIEW_SCORE = 0.55
    SAFE_DISPLAY_ALIAS_EVIDENCE = {
        "extracted from metadata",
        "extracted from key_value",
        "extracted from derived_meeting_date",
        "extracted from meeting_opening",
        "extracted from policy_title_issuer",
        "extracted from official_page_url",
        "extracted from official_page_banner",
    }
    LEGACY_ALIAS_EVIDENCE = {
        "extracted from derived_meeting_date_alias",
        "extracted from meeting_opening_alias",
        "extracted from policy_title_issuer_alias",
        "extracted from official_page_url_alias",
        "extracted from official_page_banner_alias",
    }

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
        badcases = options.get("badcases", [])
        badcases = badcases if isinstance(badcases, list) else []
        mappings: list[dict[str, Any]] = []
        review_required: list[dict[str, Any]] = []
        llm_warnings: list[dict[str, str]] = []
        llm_suggestion_count = 0
        llm_suggestion_limit = self.llm_fallback_service.settings.llm_max_suggestions_per_task
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
                mapping = self._with_decision_context(mapping, badcases)
                if mapping.need_review:
                    review_required.append(mapping.model_dump(mode="json"))
                else:
                    mappings.append(mapping.model_dump(mode="json"))
                    source_path = mapping.source_field.source_path
                    used_source_paths.add(source_path)
                    if source_path.startswith("$.metadata.source_url#"):
                        used_source_paths.add(source_path.partition("#")[0])
                strategy_counts[mapping.method] += 1
                continue

            review_item = self._find_fuzzy(task_id, field, candidates, used_source_paths)
            if (
                review_item is None
                and options.get("enable_llm_fallback")
                and llm_suggestion_count < llm_suggestion_limit
            ):
                review_item = self.llm_fallback_service.suggest_mapping(
                    task_id=task_id,
                    field=field,
                    candidates=candidates,
                    used_source_paths=used_source_paths,
                    badcases=options.get("badcases", []),
                    strict_failure=bool(
                        options.get(
                            "strict_llm",
                            self.llm_fallback_service.settings.llm_strict_failure,
                        )
                    ),
                )

            if review_item is not None:
                review_item = self._with_decision_context(review_item, badcases)
                review_data = review_item.model_dump(mode="json")
                review_required.append(review_data)
                strategy_counts[review_item.method] += 1
                if review_item.method == "llm_fallback":
                    llm_suggestion_count += 1
                    llm_metadata = review_item.llm_metadata or {}
                    if llm_metadata.get("error_code") and not llm_warnings:
                        llm_warnings.append(
                            {
                                "code": "llm_request_failed",
                                "message": (
                                    "LLM fallback request failed; human review is required."
                                ),
                            }
                        )

        mapped_targets = {mapping["target_field_id"] for mapping in mappings}
        unmapped = [
            {
                "target_field_id": field.field_id,
                "target_field_name": field.name,
                "required": field.required,
                "reason": "required field was not confirmed by deterministic mapping",
                "status": "failed",
                "confidence": 0.0,
                "confidence_tier": "low",
                "risk_flags": ["required_field_unmapped"],
                "review_required_reason": "Required target field is unmapped.",
                "evidence": [
                    MappingEvidence(
                        type="required_field_unmapped",
                        message=f"Required field '{field.field_id}' was not mapped.",
                        weight=0.0,
                    ).model_dump(mode="json")
                ],
                "evidence_text": [f"Required field '{field.field_id}' was not mapped."],
                "badcase_filter": {"checked": False, "blocked": False, "reason": None},
            }
            for field in schema.fields
            if field.required and field.field_id not in mapped_targets
        ]
        confidences = [
            item["confidence"]
            for item in [*mappings, *review_required]
            if isinstance(item.get("confidence"), int | float)
        ]
        risk_flag_counts = Counter(
            flag
            for item in [*mappings, *review_required, *unmapped]
            for flag in item.get("risk_flags", [])
        )
        accepted_count = len(mappings)
        failed_count = len(unmapped)
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        return MappingReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            summary={
                "template_id": template.template_id,
                "total_candidates": len(candidates),
                "total_target_fields": len(schema.fields),
                "mapped_count": len(mappings),
                "accepted_count": accepted_count,
                "review_required_count": len(review_required),
                "failed_count": failed_count,
                "required_unmapped_count": len(unmapped),
                "avg_confidence": avg_confidence,
                "target_fields": len(schema.fields),
                "mapped_fields": len(mappings),
                "review_required": len(review_required),
                "unmapped_required_fields": len(unmapped),
                "average_confidence": avg_confidence,
                "strategy_counts": dict(strategy_counts),
                "risk_flag_counts": dict(sorted(risk_flag_counts.items())),
                "badcase_blocked_count": risk_flag_counts.get("badcase_blocked", 0),
                "llm_suggestion_count": risk_flag_counts.get("llm_suggestion", 0),
                "warnings": llm_warnings,
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
            if any(
                evidence in self.LEGACY_ALIAS_EVIDENCE
                for evidence in candidate.evidence
            ):
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
            candidate_names = {self.normalize_name(candidate.source_name)}
            if any(
                evidence in self.SAFE_DISPLAY_ALIAS_EVIDENCE
                for evidence in candidate.evidence
            ):
                candidate_names.add(
                    self.normalize_name(candidate.display_name or "")
                )
            if candidate_names & normalized_aliases:
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

        if best_candidate is None or best_score < self.MIN_FUZZY_REVIEW_SCORE:
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
        evidence: list[Any] | None = None,
    ) -> FieldMapping:
        evidence_items, evidence_text = self._normalize_evidence(
            evidence or [f"{method} mapping to {field.field_id}"],
            default_type=f"{method}_match",
        )
        risk_flags = self.risk_flags_for_mapping(
            strategy=method,
            confidence=confidence,
            need_review=need_review,
            value_sample=candidate.value_sample,
        )
        status = "review_required" if need_review else "accepted"
        review_required_reason = self.review_reason_for_mapping(
            risk_flags=risk_flags,
            confidence=confidence,
            strategy=method,
        )
        return FieldMapping(
            mapping_id=f"map_{task_id}_{field.field_id}_{method}",
            task_id=task_id,
            candidate_id=candidate.candidate_id,
            source_field={
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            source_path=candidate.source_path,
            source_field_name=candidate.source_name,
            target_field_id=field.field_id,
            target_field_name=field.name,
            method=method,
            strategy=method,
            confidence=confidence,
            confidence_tier=self.confidence_tier(confidence),
            status=status,
            need_review=need_review,
            value_sample=candidate.value_sample,
            source_blocks=candidate.source_blocks,
            evidence=evidence_items,
            evidence_text=evidence_text,
            risk_flags=risk_flags,
            badcase_filter={"checked": False, "blocked": False, "reason": None},
            review_required_reason=review_required_reason,
        )

    def _with_decision_context(
        self,
        mapping: FieldMapping,
        badcases: list[dict[str, Any]],
    ) -> FieldMapping:
        badcase_filter = self._badcase_filter(
            mapping.source_field.source_name,
            mapping.target_field_id,
            badcases,
        )
        risk_flags = set(mapping.risk_flags)
        if badcase_filter["blocked"]:
            risk_flags.add("badcase_blocked")
        if mapping.method == "llm_fallback":
            risk_flags.add("llm_suggestion")
        need_review = (
            mapping.need_review
            or badcase_filter["blocked"]
            or mapping.method == "llm_fallback"
        )
        review_reason = self.review_reason_for_mapping(
            risk_flags=sorted(risk_flags),
            confidence=mapping.confidence,
            strategy=mapping.method,
        )
        evidence = list(mapping.evidence)
        evidence_text = list(mapping.evidence_text)
        if badcase_filter["blocked"]:
            message = str(badcase_filter["reason"])
            evidence.append(
                MappingEvidence(
                    type="badcase_filter",
                    message=message,
                    weight=1.0,
                    source="badcase",
                )
            )
            evidence_text.append(message)
        return mapping.model_copy(
            update={
                "status": "review_required" if need_review else "accepted",
                "need_review": need_review,
                "risk_flags": sorted(risk_flags),
                "badcase_filter": badcase_filter,
                "review_required_reason": review_reason,
                "evidence": evidence,
                "evidence_text": evidence_text,
            }
        )

    @staticmethod
    def confidence_tier(confidence: float | None) -> str:
        if confidence is None:
            return "low"
        if confidence >= 0.9:
            return "high"
        if confidence >= 0.7:
            return "medium"
        return "low"

    @classmethod
    def risk_flags_for_mapping(
        cls,
        *,
        strategy: str,
        confidence: float,
        need_review: bool,
        value_sample: Any | None,
    ) -> list[str]:
        flags: set[str] = set()
        if confidence < 0.7:
            flags.add("low_confidence")
        if strategy == "fuzzy":
            flags.add("fuzzy_match")
        if strategy == "llm_fallback":
            flags.add("llm_suggestion")
        if need_review and not flags:
            flags.add("review_required")
        if value_sample is None:
            flags.add("missing_value_sample")
        return sorted(flags)

    @classmethod
    def review_reason_for_mapping(
        cls,
        *,
        risk_flags: list[str],
        confidence: float,
        strategy: str,
    ) -> str | None:
        if "badcase_blocked" in risk_flags:
            return "Known badcase blocks automatic acceptance."
        if "llm_suggestion" in risk_flags:
            return "LLM suggestions always require human review."
        if "fuzzy_match" in risk_flags:
            return "Fuzzy mapping requires human review."
        if "required_field_unmapped" in risk_flags:
            return "Required target field is unmapped."
        if confidence < 0.7:
            return f"{strategy} confidence is below the review threshold."
        return None

    @staticmethod
    def _normalize_evidence(
        evidence: list[Any],
        *,
        default_type: str,
    ) -> tuple[list[MappingEvidence], list[str]]:
        items: list[MappingEvidence] = []
        text: list[str] = []
        for entry in evidence:
            if isinstance(entry, MappingEvidence):
                items.append(entry)
                text.append(entry.message)
            elif isinstance(entry, dict):
                item = MappingEvidence.model_validate(
                    {
                        "type": entry.get("type") or default_type,
                        "message": entry.get("message") or str(entry),
                        "weight": entry.get("weight"),
                        "source": entry.get("source"),
                        "metadata": entry.get("metadata") or {},
                    }
                )
                items.append(item)
                text.append(item.message)
            else:
                message = str(entry)
                items.append(MappingEvidence(type=default_type, message=message))
                text.append(message)
        return items, text

    @staticmethod
    def _badcase_filter(
        source_name: str,
        target_field_id: str,
        badcases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not badcases:
            return {"checked": False, "blocked": False, "reason": None}
        for badcase in badcases:
            if not isinstance(badcase, dict):
                continue
            if badcase.get("source_field") != source_name:
                continue
            forbidden = badcase.get("forbidden_target_fields", [])
            if isinstance(forbidden, list) and target_field_id in forbidden:
                return {
                    "checked": True,
                    "blocked": True,
                    "reason": (
                        f"Source field '{source_name}' is forbidden for "
                        f"target '{target_field_id}'."
                    ),
                }
        return {"checked": True, "blocked": False, "reason": None}

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
