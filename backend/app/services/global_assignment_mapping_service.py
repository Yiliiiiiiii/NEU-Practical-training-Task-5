from __future__ import annotations

from collections import Counter
from typing import Any

from app.schemas.mapping import FieldCandidate, MappingEvidence
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.global_assignment_solver import GlobalAssignmentSolver
from app.services.mapping_confidence_calibrator import MappingConfidenceCalibrator
from app.services.mapping_constraint_service import MappingConstraintService
from app.services.mapping_pair_feature_service import MappingPairFeatureService
from app.services.mapping_service import MappingService


class GlobalAssignmentMappingService:
    DEFAULT_AUTO_ACCEPT_THRESHOLD = 0.82
    DEFAULT_REVIEW_THRESHOLD = 0.70
    DEFAULT_MIN_CANDIDATE_SCORE = 0.45

    def __init__(
        self,
        pair_feature_service: MappingPairFeatureService | None = None,
        assignment_solver: GlobalAssignmentSolver | None = None,
        constraint_service: MappingConstraintService | None = None,
    ) -> None:
        self.pair_feature_service = pair_feature_service or MappingPairFeatureService()
        self.assignment_solver = assignment_solver or GlobalAssignmentSolver()
        self.constraint_service = constraint_service or MappingConstraintService()
        self.mapping_service = MappingService()

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
        thresholds = options.get("thresholds", {})
        thresholds = thresholds if isinstance(thresholds, dict) else {}
        calibration_payload = options.get("calibration")
        calibration_payload = calibration_payload if isinstance(calibration_payload, dict) else None
        calibrator = MappingConfidenceCalibrator(calibration_payload)
        calibrated_thresholds = (
            calibration_payload.get("thresholds", {}) if calibration_payload is not None else {}
        )
        auto_accept_threshold = float(
            options.get(
                "auto_accept_threshold",
                thresholds.get(
                    "auto_accept",
                    calibrated_thresholds.get("auto_accept", self.DEFAULT_AUTO_ACCEPT_THRESHOLD),
                ),
            )
        )
        review_threshold = float(
            options.get(
                "review_threshold",
                thresholds.get(
                    "review_required",
                    calibrated_thresholds.get("review_required", self.DEFAULT_REVIEW_THRESHOLD),
                ),
            )
        )
        min_candidate_score = float(
            options.get("min_candidate_score", self.DEFAULT_MIN_CANDIDATE_SCORE)
        )
        negative_pairs = options.get("negative_pairs", [])
        negative_pairs = negative_pairs if isinstance(negative_pairs, list) else []
        constraint_policy = self.constraint_service.policy(template.constraints, options)

        pair_rows: list[dict[str, Any]] = []
        for target in schema.fields:
            for candidate in candidates:
                features = self.pair_feature_service.build(
                    candidate,
                    target,
                    template,
                    negative_pairs=negative_pairs,
                    uir=uir,
                )
                target_minimum = self.constraint_service.minimum_score(
                    target, constraint_policy, min_candidate_score
                )
                if self.constraint_service.type_is_compatible(
                    features.type_score, constraint_policy
                ) and (features.final_score >= target_minimum or features.negative_score >= 1.0):
                    pair_rows.append(
                        {
                            "target": target,
                            "candidate": candidate,
                            "features": features,
                            "allow_source_reuse": (
                                self.constraint_service.source_reuse_allowed(
                                    candidate, target, constraint_policy
                                )
                            ),
                            "operation": self.constraint_service.operation(
                                candidate, target, constraint_policy
                            ),
                        }
                    )

        mappings: list[dict[str, Any]] = []
        review_required: list[dict[str, Any]] = []
        strategy_counts: Counter[str] = Counter()
        assigned_rows = self.assignment_solver.solve(pair_rows)
        alternatives_by_target: dict[str, list[dict[str, Any]]] = {}
        for target in schema.fields:
            alternatives_by_target[target.field_id] = sorted(
                [
                    row
                    for row in pair_rows
                    if row["target"].field_id == target.field_id
                    and row["features"].negative_score < 1.0
                ],
                key=lambda row: (
                    -row["features"].final_score,
                    row["candidate"].source_path,
                    row["candidate"].candidate_id,
                ),
            )
        selected_keys = {
            (row["target"].field_id, row["candidate"].source_path) for row in assigned_rows
        }
        conflict_skipped_count = sum(
            1
            for row in pair_rows
            if row["features"].negative_score < 1.0
            and (row["target"].field_id, row["candidate"].source_path) not in selected_keys
        )

        for row in assigned_rows:
            target: TargetField = row["target"]
            candidate: FieldCandidate = row["candidate"]
            features = row["features"]
            confidence = calibrator.calibrate(features.final_score)
            alternatives = [
                alternative
                for alternative in alternatives_by_target[target.field_id]
                if alternative["candidate"].source_path != candidate.source_path
            ][:3]
            score_margin = features.final_score - (
                alternatives[0]["features"].final_score if alternatives else 0.0
            )

            if confidence >= auto_accept_threshold:
                mappings.append(
                    self._mapping_dict(
                        task_id,
                        candidate,
                        target,
                        confidence=confidence,
                        status="accepted",
                        need_review=False,
                        features=features,
                        operation=row["operation"],
                        alternatives=alternatives,
                        score_margin=score_margin,
                        evidence_message=(f"global assignment score {features.final_score:.3f}"),
                    )
                )
                strategy_counts["global_assignment"] += 1
                continue

            if confidence >= review_threshold:
                review_required.append(
                    self._mapping_dict(
                        task_id,
                        candidate,
                        target,
                        confidence=confidence,
                        status="review_required",
                        need_review=True,
                        features=features,
                        operation=row["operation"],
                        alternatives=alternatives,
                        score_margin=score_margin,
                        evidence_message=(
                            f"global assignment review score {features.final_score:.3f}"
                        ),
                    )
                )
                strategy_counts["global_assignment_review"] += 1

        assigned_target_ids = {row["target"].field_id for row in assigned_rows}
        blocked_by_target: dict[str, dict[str, Any]] = {}
        for row in sorted(
            pair_rows,
            key=lambda item: (
                item["target"].field_id,
                item["candidate"].source_path,
                item["candidate"].candidate_id,
            ),
        ):
            target_id = row["target"].field_id
            if target_id not in assigned_target_ids and row["features"].negative_score >= 1.0:
                blocked_by_target.setdefault(target_id, row)
        for row in blocked_by_target.values():
            review_required.append(
                self._mapping_dict(
                    task_id,
                    row["candidate"],
                    row["target"],
                    confidence=0.0,
                    status="blocked",
                    need_review=True,
                    features=row["features"],
                    operation=row["operation"],
                    evidence_message="negative pair blocked automatic mapping",
                )
            )
            strategy_counts["global_assignment_blocked"] += 1

        resolved_targets = {
            item["target_field_id"]
            for item in [*mappings, *review_required]
            if item.get("status") != "blocked"
        }
        source_present_targets = {
            row["target"].field_id
            for row in pair_rows
            if row["features"].final_score >= min_candidate_score
            and row["features"].negative_score < 1.0
        }
        unmapped = [
            self._unmapped_dict(
                field,
                source_present=field.field_id in source_present_targets,
            )
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
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        return MappingReport(
            task_id=task_id,
            schema_id=schema.schema_id,
            summary={
                "template_id": template.template_id,
                "mapping_mode": "global_assignment",
                "assignment_algorithm": "maximum_weight_bipartite",
                "assignment_dummy_node_count": len(schema.fields),
                "total_candidates": len(candidates),
                "total_target_fields": len(schema.fields),
                "pair_count": len(pair_rows),
                "conflict_skipped_count": conflict_skipped_count,
                "auto_accept_threshold": auto_accept_threshold,
                "review_threshold": review_threshold,
                "mapped_count": len(mappings),
                "accepted_count": len(mappings),
                "review_required_count": len(review_required),
                "failed_count": len(unmapped),
                "required_unmapped_count": len(unmapped),
                "avg_confidence": avg_confidence,
                "target_fields": len(schema.fields),
                "mapped_fields": len(mappings),
                "review_required": len(review_required),
                "unmapped_required_fields": len(unmapped),
                "average_confidence": avg_confidence,
                "strategy_counts": dict(strategy_counts),
                "risk_flag_counts": dict(sorted(risk_flag_counts.items())),
                "badcase_blocked_count": risk_flag_counts.get("negative_pair_block", 0),
                "llm_suggestion_count": 0,
                "warnings": [],
                "methods": {key: value for key, value in strategy_counts.items() if value},
                "thresholds": thresholds,
            },
            mappings=mappings,
            unmapped=unmapped,
            review_required_items=review_required,
        )

    def _mapping_dict(
        self,
        task_id: str,
        candidate: FieldCandidate,
        target: TargetField,
        *,
        confidence: float,
        status: str,
        need_review: bool,
        features: Any,
        operation: str = "one_to_one",
        alternatives: list[dict[str, Any]] | None = None,
        score_margin: float = 0.0,
        evidence_message: str,
    ) -> dict[str, Any]:
        mapping = self.mapping_service._mapping(
            task_id=task_id,
            candidate=candidate,
            field=target,
            method="global_assignment",
            confidence=confidence,
            need_review=need_review,
            evidence=[
                MappingEvidence(
                    type="global_assignment",
                    message=evidence_message,
                    weight=confidence,
                )
            ],
            ranking_trace=self._feature_trace(features),
        )
        data = mapping.model_dump(mode="json")
        risk_flags = sorted({*data.get("risk_flags", []), *features.risk_flags})
        data.update(
            {
                "status": status,
                "operation": operation,
                "need_review": need_review,
                "risk_flags": risk_flags,
                "confidence_tier": self.mapping_service.confidence_tier(confidence),
                "review_required_reason": (
                    "Known negative pair blocks automatic acceptance."
                    if status == "blocked"
                    else data.get("review_required_reason")
                ),
            }
        )
        alternative_rows = [
            {
                "candidate_id": row["candidate"].candidate_id,
                "source_path": row["candidate"].source_path,
                "source_name": row["candidate"].source_name,
                "score": row["features"].final_score,
            }
            for row in alternatives or []
        ]
        data["rejected_candidates"] = alternative_rows
        data["ranking_trace"]["calibrated_confidence"] = confidence
        data["ranking_trace"]["score_margin"] = round(score_margin, 4)
        data["decision_trace"] = {
            "top_candidate": {
                "candidate_id": candidate.candidate_id,
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            "top_alternatives": alternative_rows,
            "calibrated_confidence": confidence,
            "score_margin": round(score_margin, 4),
            "feature_trace": self._feature_trace(features),
            "risk_flags": risk_flags,
            "negative_pair_checks": {
                "checked": True,
                "blocked": status == "blocked",
            },
            "review_reason": data.get("review_required_reason"),
            "source_backlinks": {
                "source_path": candidate.source_path,
                "source_blocks": list(candidate.source_blocks),
            },
        }
        if status == "blocked":
            data["badcase_filter"] = {
                "checked": True,
                "blocked": True,
                "reason": "negative_pair_block",
                "source": "configured_rules",
            }
        return data

    @staticmethod
    def _feature_trace(features: Any) -> dict[str, float]:
        return {
            "final_score": features.final_score,
            "lexical_score": features.lexical_score,
            "alias_score": features.alias_score,
            "type_score": features.type_score,
            "value_score": features.value_score,
            "path_score": features.path_score,
            "context_score": features.context_score,
            "evidence_score": features.evidence_score,
            "negative_score": features.negative_score,
            "source_quality_score": features.source_quality_score,
        }

    @staticmethod
    def _unmapped_dict(
        field: TargetField,
        *,
        source_present: bool,
    ) -> dict[str, Any]:
        return {
            "target_field_id": field.field_id,
            "target_field_name": field.name,
            "required": field.required,
            "source_present": source_present,
            "reason": "required field was not confirmed by global assignment",
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
