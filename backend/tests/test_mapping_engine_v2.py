from __future__ import annotations

from app.schemas.mapping_features import MappingPairFeatures
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.field_descriptor_service import FieldDescriptorService
from app.services.global_assignment_mapping_service import GlobalAssignmentMappingService
from app.services.mapping_confidence_calibrator import (
    CalibrationSample,
    MappingConfidenceCalibrator,
)


def _field(field_id: str, *aliases: str, required: bool = False) -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id.replace("_", " "),
        type="string",
        required=required,
        aliases=list(aliases),
    )


def _uir(*blocks: dict[str, object]) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "descriptor-doc",
            "metadata": {"domain": "unseen_schema"},
            "blocks": list(blocks),
            "assets": [],
            "normalization_records": [],
        }
    )


def test_generic_labeled_blocks_are_candidates_without_target_hints() -> None:
    uir = _uir(
        {
            "block_id": "kv",
            "type": "key_value",
            "text": "Official public name of the scheduled event: Open Day",
            "attributes": {},
        },
        {
            "block_id": "table",
            "type": "table",
            "text": "Event venue | Hall A",
            "attributes": {},
        },
        {
            "block_id": "paragraph",
            "type": "paragraph",
            "text": "Registration due: 2026-08-01",
            "attributes": {},
        },
    )

    candidates = CandidateService().extract_candidates(
        "descriptor-doc", uir, enable_legacy_domain_rules=False
    )
    pairs = {(item.source_path, item.source_name) for item in candidates}

    assert (
        "$.blocks.kv.text",
        "Official public name of the scheduled event",
    ) in pairs
    assert ("$.blocks.table.text", "Event venue") in pairs
    assert ("$.blocks.paragraph.text", "Registration due") in pairs
    assert all(
        not item.target_hints
        for item in candidates
        if item.source_path
        in {
            "$.blocks.kv.text",
            "$.blocks.table.text",
            "$.blocks.paragraph.text",
        }
    )


def test_mapping_template_accepts_strict_v2_scoring_policy() -> None:
    template = MappingTemplate.model_validate(
        {
            "template_id": "unseen-v2",
            "schema_id": "unseen_schema",
            "name": "Unseen",
            "version": "2.0.0",
            "scoring": {
                "lexical_weight": 0.25,
                "alias_weight": 0.2,
                "type_weight": 0.15,
                "value_shape_weight": 0.1,
                "path_weight": 0.1,
                "context_weight": 0.1,
                "source_quality_weight": 0.1,
            },
            "evidence_weights": {
                "metadata": 0.8,
                "key_value": 0.85,
                "table": 0.9,
                "block": 0.7,
            },
        }
    )

    assert template.scoring.lexical_weight == 0.25
    assert template.evidence_weights["table"] == 0.9


def test_schema_held_out_descriptors_use_only_contract_and_uir() -> None:
    uir = _uir(
        {
            "block_id": "b1",
            "type": "key_value",
            "text": "Unseen label: Example",
            "attributes": {"title_path": ["Section A"]},
        }
    )
    candidate = next(
        item
        for item in CandidateService().extract_candidates(
            "descriptor-doc", uir, enable_legacy_domain_rules=False
        )
        if item.source_name == "Unseen label"
    )
    field = TargetField(
        field_id="novel_field",
        name="novel_field",
        display_name="Novel Field",
        description="A field from a schema not seen during tuning.",
        type="string",
        required=True,
        aliases=["Unseen label"],
        parent_path="$.details",
        constraints={"enum": ["Example"], "maxLength": 80},
    )
    template = MappingTemplate(
        template_id="unseen-v2",
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        aliases={"novel_field": ["Unseen label"]},
    )

    service = FieldDescriptorService()
    target = service.target_descriptor(field, template)
    source = service.candidate_descriptor(candidate, uir)

    assert target.parent_path == "$.details"
    assert target.enum_values == ["Example"]
    assert target.format_constraints == {"maxLength": 80}
    assert source.block_type == "key_value"
    assert source.section_title_path == ["Section A"]


def test_blocked_alternative_does_not_hide_valid_candidate() -> None:
    uir = _uir(
        {
            "block_id": "blocked",
            "type": "paragraph",
            "text": "Event date: 2026-01-01",
            "attributes": {"field_name": "publish date"},
        },
        {
            "block_id": "valid",
            "type": "paragraph",
            "text": "Event date: 2026-02-01",
            "attributes": {"field_name": "event date"},
        },
    )
    candidates = CandidateService().extract_candidates(
        "descriptor-doc", uir, enable_legacy_domain_rules=False
    )
    schema = TargetSchema(
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        fields=[_field("event_date", "event date", required=True)],
    )
    template = MappingTemplate(
        template_id="unseen-v2",
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        aliases={"event_date": ["event date", "publish date"]},
    )

    report = GlobalAssignmentMappingService().map_fields(
        "descriptor-doc",
        uir,
        schema,
        template,
        candidates,
        {
            "auto_accept_threshold": 0.6,
            "negative_pairs": [
                {
                    "source_path": "$.blocks.blocked.text",
                    "target_field_id": "event_date",
                    "reason": "publication is not event date",
                }
            ],
        },
    )

    assert report.mappings[0]["source_path"] == "$.blocks.valid.text"
    assert report.unmapped == []


class _ScoreMatrix:
    def __init__(self, scores: dict[tuple[str, str], float]) -> None:
        self.scores = scores

    def build(self, candidate, target, template, *, negative_pairs=None, uir=None):
        score = self.scores[(target.field_id, candidate.candidate_id)]
        return MappingPairFeatures(
            source_candidate_id=candidate.candidate_id,
            source_path=candidate.source_path,
            source_name=candidate.source_name,
            target_field_id=target.field_id,
            target_name=target.name,
            lexical_score=score,
            alias_score=0.0,
            type_score=1.0,
            value_score=1.0,
            path_score=0.0,
            context_score=0.0,
            evidence_score=1.0,
            negative_score=0.0,
            source_quality_score=1.0,
            final_score=score,
        )


def test_true_global_assignment_beats_greedy_counterexample() -> None:
    uir = _uir(
        {
            "block_id": "x",
            "type": "paragraph",
            "text": "x",
            "attributes": {"field_name": "x"},
        },
        {
            "block_id": "y",
            "type": "paragraph",
            "text": "y",
            "attributes": {"field_name": "y"},
        },
    )
    candidates = [
        item
        for item in CandidateService().extract_candidates(
            "descriptor-doc", uir, enable_legacy_domain_rules=False
        )
        if item.source_name in {"x", "y"}
    ]
    by_name = {item.source_name: item for item in candidates}
    by_name["x"] = by_name["x"].model_copy(update={"candidate_id": "x"})
    by_name["y"] = by_name["y"].model_copy(update={"candidate_id": "y"})
    schema = TargetSchema(
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        fields=[_field("a"), _field("b")],
    )
    service = GlobalAssignmentMappingService(
        pair_feature_service=_ScoreMatrix(
            {("a", "x"): 0.90, ("a", "y"): 0.80, ("b", "x"): 0.89, ("b", "y"): 0.10}
        )
    )
    report = service.map_fields(
        "descriptor-doc",
        uir,
        schema,
        MappingTemplate(
            template_id="unseen-v2",
            schema_id="unseen_schema",
            name="Unseen",
            version="2.0.0",
        ),
        [by_name["x"], by_name["y"]],
        {"auto_accept_threshold": 0.0, "min_candidate_score": 0.0},
    )

    assert {item["target_field_id"]: item["candidate_id"] for item in report.mappings} == {
        "a": "y",
        "b": "x",
    }
    assert report.summary["assignment_algorithm"] == "maximum_weight_bipartite"


def test_global_assignment_tie_is_stable_across_input_order() -> None:
    uir = _uir(
        {
            "block_id": "x",
            "type": "paragraph",
            "text": "x",
            "attributes": {"field_name": "x"},
        },
        {
            "block_id": "y",
            "type": "paragraph",
            "text": "y",
            "attributes": {"field_name": "y"},
        },
    )
    candidates = [
        item.model_copy(update={"candidate_id": item.source_name})
        for item in CandidateService().extract_candidates(
            "descriptor-doc", uir, enable_legacy_domain_rules=False
        )
        if item.source_name in {"x", "y"}
    ]
    schema = TargetSchema(
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        fields=[_field("a"), _field("b")],
    )
    service = GlobalAssignmentMappingService(
        pair_feature_service=_ScoreMatrix(
            {(target, source): 0.9 for target in ("a", "b") for source in ("x", "y")}
        )
    )
    template = MappingTemplate(
        template_id="unseen-v2",
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
    )

    first = service.map_fields(
        "descriptor-doc",
        uir,
        schema,
        template,
        candidates,
        {"auto_accept_threshold": 0.0, "min_candidate_score": 0.0},
    )
    second = service.map_fields(
        "descriptor-doc",
        uir,
        schema,
        template,
        list(reversed(candidates)),
        {"auto_accept_threshold": 0.0, "min_candidate_score": 0.0},
    )

    assert [(item["target_field_id"], item["source_path"]) for item in first.mappings] == [
        (item["target_field_id"], item["source_path"]) for item in second.mappings
    ]


def test_source_reuse_requires_an_explicit_rule() -> None:
    uir = _uir(
        {
            "block_id": "shared",
            "type": "paragraph",
            "text": "shared",
            "attributes": {"field_name": "shared"},
        }
    )
    candidate = next(
        item.model_copy(update={"candidate_id": "shared"})
        for item in CandidateService().extract_candidates(
            "descriptor-doc", uir, enable_legacy_domain_rules=False
        )
        if item.source_name == "shared"
    )
    schema = TargetSchema(
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        fields=[_field("a"), _field("b")],
    )
    service = GlobalAssignmentMappingService(
        pair_feature_service=_ScoreMatrix({("a", "shared"): 0.9, ("b", "shared"): 0.9})
    )
    template = MappingTemplate(
        template_id="unseen-v2",
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
    )
    base_options = {"auto_accept_threshold": 0.0, "min_candidate_score": 0.0}

    default_report = service.map_fields(
        "descriptor-doc", uir, schema, template, [candidate], base_options
    )
    reuse_report = service.map_fields(
        "descriptor-doc",
        uir,
        schema,
        template,
        [candidate],
        {
            **base_options,
            "constraints": {
                "source_reuse_rules": [
                    {
                        "source_path": "$.blocks.shared.text",
                        "target_field_ids": ["a", "b"],
                        "reason": "one source explicitly feeds two targets",
                    }
                ]
            },
        },
    )

    assert len(default_report.mappings) == 1
    assert {item["target_field_id"] for item in reuse_report.mappings} == {"a", "b"}


def test_non_default_cardinality_is_emitted_only_by_rule() -> None:
    uir = _uir(
        {
            "block_id": "part",
            "type": "paragraph",
            "text": "part",
            "attributes": {"field_name": "part"},
        }
    )
    candidate = next(
        item.model_copy(update={"candidate_id": "part"})
        for item in CandidateService().extract_candidates(
            "descriptor-doc", uir, enable_legacy_domain_rules=False
        )
        if item.source_name == "part"
    )
    schema = TargetSchema(
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
        fields=[_field("combined")],
    )
    service = GlobalAssignmentMappingService(
        pair_feature_service=_ScoreMatrix({("combined", "part"): 0.9})
    )
    template = MappingTemplate(
        template_id="unseen-v2",
        schema_id="unseen_schema",
        name="Unseen",
        version="2.0.0",
    )
    base_options = {"auto_accept_threshold": 0.0, "min_candidate_score": 0.0}

    plain = service.map_fields("descriptor-doc", uir, schema, template, [candidate], base_options)
    declared = service.map_fields(
        "descriptor-doc",
        uir,
        schema,
        template,
        [candidate],
        {
            **base_options,
            "constraints": {
                "cardinality_rules": [
                    {
                        "operation": "many_to_one",
                        "target_field_id": "combined",
                        "source_paths": ["$.blocks.part.text"],
                        "reason": "declared merge input",
                    }
                ]
            },
        },
    )

    assert plain.mappings[0]["operation"] == "one_to_one"
    assert declared.mappings[0]["operation"] == "many_to_one"


def test_dev_calibrator_is_monotonic_and_reports_calibration_metrics() -> None:
    samples = [
        CalibrationSample(0.15, False),
        CalibrationSample(0.25, False),
        CalibrationSample(0.45, True),
        CalibrationSample(0.55, False),
        CalibrationSample(0.75, True),
        CalibrationSample(0.85, True),
        CalibrationSample(0.95, True),
    ]

    artifact = MappingConfidenceCalibrator.fit(samples, bin_count=5)
    calibrator = MappingConfidenceCalibrator(artifact)
    calibrated = [calibrator.calibrate(index / 100) for index in range(101)]

    assert artifact["fit_split"] == "dev"
    assert calibrated == sorted(calibrated)
    assert 0.0 <= artifact["brier_score"] <= 1.0
    assert 0.0 <= artifact["expected_calibration_error"] <= 1.0
    assert artifact["reliability_bins"]
    assert artifact["precision_coverage_curve"]
