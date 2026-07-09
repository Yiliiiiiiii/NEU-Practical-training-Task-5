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
    AUTO_ACCEPT_SCORE = 0.82
    MIN_EVIDENCE_REVIEW_SCORE = 0.55
    NO_FUZZY_WITHOUT_HINT_TARGETS = {
        "action_items",
        "agenda_items",
        "created_date",
        "deadline",
        "deadlines",
        "decisions",
        "document_subtype",
        "issuer",
        "organizer",
    }
    FORBIDDEN_PAIRS = {
        ("成文日期", "publish_date"): "forbidden_issue_date_to_publish_date",
        ("发布日期", "effective_date"): "forbidden_publish_date_to_effective_date",
        ("retrieved_at", "effective_date"): "forbidden_retrieval_time_to_effective_date",
        ("主持人", "attendees"): "forbidden_chairperson_to_attendees",
        ("联系人", "attendees"): "forbidden_contact_to_attendees",
        ("联系人", "service_object"): "forbidden_contact_to_service_object",
        ("承办单位", "issuer"): "forbidden_organizer_to_issuer",
        ("解读机构", "issuer"): "forbidden_interpreter_to_issuer",
        ("预算金额", "award_amount"): "forbidden_budget_to_award",
        ("控制价", "award_amount"): "forbidden_control_price_to_award",
    }
    SAFE_DISPLAY_ALIAS_EVIDENCE = {
        "extracted from metadata",
        "extracted from key_value",
        "extracted from derived_meeting_date",
        "extracted from meeting_opening",
        "extracted from policy_title_issuer",
        "extracted from policy_signature_date",
        "extracted from official_page_url",
        "extracted from official_page_banner",
    }
    LEGACY_ALIAS_EVIDENCE = {
        "extracted from derived_meeting_date_alias",
        "extracted from meeting_opening_alias",
        "extracted from policy_title_issuer_alias",
        "extracted from policy_standalone_issuer_alias",
        "extracted from policy_signature_issuer_alias",
        "extracted from policy_announcement_header_issuer_alias",
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
        negative_pairs = options.get("negative_pairs", [])
        negative_pairs = negative_pairs if isinstance(negative_pairs, list) else []
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
                mapping = self._find_evidence_ranked(
                    task_id,
                    field,
                    candidates,
                    used_source_paths,
                )
            if mapping is None:
                mapping = self._find_type(task_id, field, candidates, used_source_paths)

            if mapping is not None:
                mapping = self._with_decision_context(mapping, badcases, negative_pairs)
                if mapping.need_review:
                    review_required.append(mapping.model_dump(mode="json"))
                else:
                    mappings.append(mapping.model_dump(mode="json"))
                    source_path = mapping.source_field.source_path
                    used_source_paths.add(source_path)
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
                review_item = self._with_decision_context(review_item, badcases, negative_pairs)
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
        review_supported_targets = {
            item["target_field_id"]
            for item in review_required
            if item.get("status") == "review_required"
            and item.get("method") not in {"fuzzy", "llm_fallback"}
        }
        resolved_targets = mapped_targets | review_supported_targets
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
            if field.required and field.field_id not in resolved_targets
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
                "thresholds": options.get("thresholds", {}),
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
        matched: list[FieldCandidate] = []
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            if any(
                evidence in self.LEGACY_ALIAS_EVIDENCE
                for evidence in candidate.evidence
            ):
                continue
            if self.normalize_name(candidate.source_name) in target_names:
                matched.append(candidate)
        if not matched:
            return None
        selected, trace, rejected = self._rank_candidates(
            matched,
            field,
            label_matched=True,
        )
        need_review = bool(selected.quality_flags) or (
            self._builtin_forbidden_reason(selected.source_name, field.field_id)
            is not None
        )
        return self._mapping(
            task_id,
            selected,
            field,
            "exact",
            1.0,
            need_review,
            ranking_trace=trace,
            rejected_candidates=rejected,
        )

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
        matched: list[FieldCandidate] = []
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
                matched.append(candidate)
        matched_ids = {candidate.candidate_id for candidate in matched}
        matched.extend(
            candidate
            for candidate in candidates
            if candidate.candidate_id not in matched_ids
            and candidate.source_path not in used_source_paths
            and field.field_id in candidate.target_hints
        )
        if not matched:
            return None
        selected, trace, rejected = self._rank_candidates(
            matched,
            field,
            label_matched=True,
        )
        need_review = bool(selected.quality_flags) or (
            self._builtin_forbidden_reason(selected.source_name, field.field_id)
            is not None
        )
        return self._mapping(
            task_id,
            selected,
            field,
            "alias",
            0.96,
            need_review,
            evidence=[f"alias matched target {field.field_id}"],
            ranking_trace=trace,
            rejected_candidates=rejected,
        )

    def _find_evidence_ranked(
        self,
        task_id: str,
        field: TargetField,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
    ) -> FieldMapping | None:
        eligible = [
            candidate
            for candidate in candidates
            if candidate.source_path not in used_source_paths
            and (
                field.field_id in candidate.target_hints
                or (
                    candidate.evidence_type == "paragraph_regex"
                    and self.normalize_name(candidate.display_name or "")
                    == self.normalize_name(field.field_id)
                )
            )
        ]
        if not eligible:
            return None
        selected, trace, rejected = self._rank_candidates(eligible, field)
        final_score = trace["final_score"]
        if final_score < self.MIN_EVIDENCE_REVIEW_SCORE:
            return None
        need_review = (
            final_score < self.AUTO_ACCEPT_SCORE
            or bool(selected.quality_flags)
            or self._builtin_forbidden_reason(
                selected.source_name,
                field.field_id,
            )
            is not None
        )
        return self._mapping(
            task_id,
            selected,
            field,
            "evidence_ranked",
            final_score,
            need_review,
            evidence=[
                {
                    "type": "evidence_ranked",
                    "message": (
                        f"evidence-aware score {final_score:.3f} for "
                        f"target {field.field_id}"
                    ),
                    "weight": final_score,
                }
            ],
            ranking_trace=trace,
            rejected_candidates=rejected,
        )

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
        if field.field_id in self.NO_FUZZY_WITHOUT_HINT_TARGETS:
            return None
        best_candidate: FieldCandidate | None = None
        best_score = 0.0
        field_terms = [field.field_id, field.name, field.display_name, *field.aliases]
        for candidate in candidates:
            if candidate.source_path in used_source_paths:
                continue
            forbidden_reason = self._builtin_forbidden_reason(
                candidate.source_name,
                field.field_id,
            )
            if (
                forbidden_reason
                and self.normalize_name(candidate.source_name) == "retrievedat"
                and field.field_id == "effective_date"
            ):
                continue
            if field.field_id == "issuer" and not self._issuer_like_source(
                candidate.source_name
            ):
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

    @classmethod
    def _issuer_like_source(cls, source_name: str) -> bool:
        normalized = cls.normalize_name(source_name)
        return any(
            marker in normalized
            for marker in (
                "issuer",
                "主体",
                "机关",
                "机构",
                "单位",
                "部门",
            )
        )

    def _rank_candidates(
        self,
        candidates: list[FieldCandidate],
        field: TargetField,
        *,
        label_matched: bool = False,
    ) -> tuple[FieldCandidate, dict[str, float], list[dict[str, Any]]]:
        ranked = [
            (self._ranking_trace(candidate, field, label_matched=label_matched), index, candidate)
            for index, candidate in enumerate(candidates)
        ]
        ranked.sort(
            key=lambda item: (
                -item[0]["final_score"],
                -float(item[2].confidence_hint or item[2].confidence),
                item[1],
            )
        )
        selected_trace, _selected_index, selected = ranked[0]
        rejected = [
            {
                "candidate_id": candidate.candidate_id,
                "source_name": candidate.source_name,
                "target_field": field.field_id,
                "reason": "lower_evidence_score",
                "final_score": trace["final_score"],
            }
            for trace, _index, candidate in ranked[1:]
        ]
        return selected, selected_trace, rejected

    def _ranking_trace(
        self,
        candidate: FieldCandidate,
        field: TargetField,
        *,
        label_matched: bool = False,
    ) -> dict[str, float]:
        terms = [
            field.field_id,
            field.name,
            field.display_name,
            *field.aliases,
        ]
        labels = [candidate.source_name, candidate.display_name or ""]
        label_score = max(
            (
                self._similarity(label, term)
                for label in labels
                for term in terms
                if label and term
            ),
            default=0.0,
        )
        if field.field_id in candidate.target_hints:
            label_score = 1.0
        if label_matched:
            label_score = 1.0

        evidence_type = candidate.evidence_type or ""
        evidence_score = {
            "official_issuer_metadata": 1.0,
            "official_publication_metadata": 1.0,
            "official_source_url": 1.0,
            "official_source_metadata": 0.85,
            "official_publication_url": 0.9,
            "official_attachment_url": 0.95,
            "official_page_banner": 0.95,
            "policy_signature": 0.95,
            "policy_signature_date": 1.0,
            "policy_signature_issuer_alias": 0.35,
            "policy_publish_date_label": 0.95,
            "policy_issuer_label": 0.9,
            "policy_effective_date_sentence": 0.95,
            "policy_valid_until_sentence": 0.95,
            "policy_measures_section": 0.95,
            "policy_document_number": 0.95,
            "policy_target_audience_label": 0.95,
            "policy_notice_addressee": 0.5,
            "service_object_section": 0.95,
            "service_object_labeled_sentence": 0.95,
            "general_contact_label": 0.95,
            "process_steps_labeled_sentence": 0.95,
            "application_conditions_section": 0.95,
            "agenda_section": 0.9,
            "explicit_meeting_date": 0.95,
            "meeting_number_pattern": 0.9,
            "meeting_opening": 0.9,
            "meeting_opening_alias": 0.4,
            "policy_title_issuer": 0.9,
            "policy_title_issuer_alias": 0.4,
            "official_page_url_alias": 0.4,
            "official_page_banner_alias": 0.4,
            "derived_meeting_date_alias": 0.4,
            "aggregate_blocks": 1.0,
            "key_value": 0.85,
            "table": 0.9,
            "metadata": 0.8,
            "page_publisher_field": 0.45,
            "page_publisher_metadata": 0.45,
            "page_column": 0.4,
            "paragraph_regex": 0.9,
        }.get(evidence_type, 0.7 if candidate.source_blocks else 0.6)

        normalized_path = self.normalize_name(candidate.source_path)
        normalized_target = self.normalize_name(field.field_id)
        if field.field_id in candidate.target_hints:
            context_score = 0.95
        elif normalized_target and normalized_target in normalized_path:
            context_score = 0.85
        elif candidate.source_blocks:
            context_score = 0.7
        elif candidate.source_path.startswith("$.metadata."):
            context_score = 0.75
        else:
            context_score = 0.5

        type_score = self._type_score(candidate.inferred_type, field.type)
        if candidate.source_blocks and candidate.source_path:
            source_quality_score = 0.95
        elif candidate.source_path.startswith("$.metadata."):
            source_quality_score = 0.85
        elif candidate.source_path:
            source_quality_score = 0.6
        else:
            source_quality_score = 0.0

        risk_penalty = self._risk_penalty(candidate, field.field_id)
        final_score = (
            label_score * 0.35
            + evidence_score * 0.30
            + context_score * 0.20
            + type_score * 0.10
            + source_quality_score * 0.05
            - risk_penalty
        )
        return {
            "label_score": round(label_score, 4),
            "evidence_score": round(evidence_score, 4),
            "context_score": round(context_score, 4),
            "type_score": round(type_score, 4),
            "source_quality_score": round(source_quality_score, 4),
            "risk_penalty": round(risk_penalty, 4),
            "final_score": round(max(0.0, min(final_score, 1.0)), 4),
        }

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

    def _risk_penalty(
        self,
        candidate: FieldCandidate,
        target_field_id: str,
    ) -> float:
        if self._builtin_forbidden_reason(candidate.source_name, target_field_id):
            return 1.0
        flags = set(candidate.quality_flags)
        penalty = 0.0
        if any("high" in flag for flag in flags):
            penalty += 0.5
        if any("medium" in flag for flag in flags):
            penalty += 0.2
        if "weak_evidence" in flags:
            penalty += 0.25
        if "synthetic_alias" in flags:
            penalty += 0.15
        if not candidate.source_path:
            penalty += 0.4
        return min(penalty, 1.0)

    def _mapping(
        self,
        task_id: str,
        candidate: FieldCandidate,
        field: TargetField,
        method: str,
        confidence: float,
        need_review: bool,
        evidence: list[Any] | None = None,
        ranking_trace: dict[str, float] | None = None,
        rejected_candidates: list[dict[str, Any]] | None = None,
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
        risk_flags = sorted({*risk_flags, *candidate.quality_flags})
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
            ranking_trace=ranking_trace or self._ranking_trace(candidate, field),
            rejected_candidates=rejected_candidates or [],
        )

    def _with_decision_context(
        self,
        mapping: FieldMapping,
        badcases: list[dict[str, Any]],
        negative_pairs: list[dict[str, Any]] | None = None,
    ) -> FieldMapping:
        badcase_filter = self._badcase_filter(
            mapping.source_field.source_name,
            mapping.target_field_id,
            badcases,
        )
        forbidden_reason = self._builtin_forbidden_reason(
            mapping.source_field.source_name,
            mapping.target_field_id,
        )
        configured_reason = self._configured_forbidden_reason(
            mapping.source_field.source_name,
            mapping.target_field_id,
            negative_pairs or [],
        )
        if configured_reason is not None:
            badcase_filter = {
                "checked": True,
                "blocked": True,
                "reason": configured_reason,
                "source": "configured_rules",
            }
        if forbidden_reason is not None:
            badcase_filter = {
                "checked": True,
                "blocked": True,
                "reason": forbidden_reason,
                "source": "builtin_rules",
            }
        risk_flags = set(mapping.risk_flags)
        if badcase_filter["blocked"]:
            risk_flags.add("badcase_blocked")
        if configured_reason is not None:
            risk_flags.add("configured_negative_pair")
        if forbidden_reason is not None:
            risk_flags.add("forbidden_pair")
        if mapping.method == "llm_fallback":
            risk_flags.add("llm_suggestion")
        need_review = (
            mapping.need_review
            or badcase_filter["blocked"]
            or mapping.method == "llm_fallback"
            or self._requires_review_for_risk(risk_flags)
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
                    source=str(badcase_filter.get("source") or "badcase"),
                )
            )
            evidence_text.append(message)
        return mapping.model_copy(
            update={
                "status": (
                    "blocked"
                    if badcase_filter["blocked"]
                    else "review_required"
                    if need_review
                    else "accepted"
                ),
                "need_review": need_review,
                "risk_flags": sorted(risk_flags),
                "badcase_filter": badcase_filter,
                "review_required_reason": review_reason,
                "evidence": evidence,
                "evidence_text": evidence_text,
            }
        )

    @staticmethod
    def _configured_forbidden_reason(
        source_name: str,
        target_field_id: str,
        negative_pairs: list[dict[str, Any]],
    ) -> str | None:
        for item in negative_pairs:
            if not isinstance(item, dict):
                continue
            pattern = item.get("source_pattern")
            target = item.get("target_field_id")
            if (
                target == target_field_id
                and isinstance(pattern, str)
                and re.search(pattern, source_name)
            ):
                return str(item.get("reason") or "configured_negative_pair")
        return None

    @staticmethod
    def _requires_review_for_risk(risk_flags: set[str]) -> bool:
        return any(
            "medium" in flag or "high" in flag or flag == "weak_evidence"
            for flag in risk_flags
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
        if any("medium" in flag or "high" in flag for flag in risk_flags):
            return "Mapping evidence has semantic risk and requires human review."
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

    @classmethod
    def _builtin_forbidden_reason(
        cls,
        source_name: str,
        target_field_id: str,
    ) -> str | None:
        normalized_source = cls.normalize_name(source_name)
        for (source, target), reason in cls.FORBIDDEN_PAIRS.items():
            if (
                target == target_field_id
                and cls.normalize_name(source) == normalized_source
            ):
                return reason
        return None

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
