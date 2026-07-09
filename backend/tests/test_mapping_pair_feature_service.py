from __future__ import annotations

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField
from app.services.mapping_pair_feature_service import MappingPairFeatureService


def make_candidate(
    *,
    source_name: str,
    source_path: str = "$.blocks.b1.text",
    value: object = "2026-07-12",
    inferred_type: str = "string",
    target_hints: list[str] | None = None,
    evidence_type: str = "key_value",
    source_blocks: list[str] | None = None,
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id="cand-1",
        task_id="task-1",
        doc_id="doc-1",
        source_path=source_path,
        source_name=source_name,
        display_name=source_name,
        value_sample=value,
        inferred_type=inferred_type,
        source_blocks=source_blocks if source_blocks is not None else ["b1"],
        confidence=0.9,
        evidence=[f"extracted from {evidence_type}"],
        evidence_type=evidence_type,
        target_hints=target_hints or [],
        confidence_hint=0.9,
    )


def make_field(field_id: str, field_type: str = "string") -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id.replace("_", " "),
        type=field_type,
        aliases=[field_id.replace("_", " ")],
    )


def make_template() -> MappingTemplate:
    return MappingTemplate(
        template_id="event_notice_doc_base_v1",
        schema_id="event_notice_doc",
        name="Event Notice",
        version="1.0.0",
        aliases={"event_time": ["event time", "start time"]},
    )


def test_pair_feature_alias_match_scores_high() -> None:
    features = MappingPairFeatureService().build(
        make_candidate(source_name="event time"),
        make_field("event_time", "datetime"),
        make_template(),
    )

    assert features.alias_score == 1.0
    assert features.lexical_score >= 0.9
    assert features.final_score >= 0.8
    assert "alias_match" in features.reasons


def test_pair_feature_negative_pair_scores_zero() -> None:
    features = MappingPairFeatureService().build(
        make_candidate(source_name="publish date"),
        make_field("event_time", "datetime"),
        make_template(),
        negative_pairs=[
            {
                "schema_id": "event_notice_doc",
                "source_pattern": "publish date|retrieved_at",
                "target_field_id": "event_time",
                "reason": "publish date is not event time",
                "severity": "block",
            }
        ],
    )

    assert features.negative_score == 1.0
    assert features.final_score == 0.0
    assert "negative_pair_block" in features.risk_flags


def test_pair_feature_date_value_score() -> None:
    features = MappingPairFeatureService().build(
        make_candidate(source_name="publish_date", value="2026-07-09", inferred_type="date"),
        make_field("publish_date", "date"),
        MappingTemplate(
            template_id="policy_doc_base_v1",
            schema_id="policy_doc",
            name="Policy",
            version="1.0.0",
            aliases={},
        ),
    )

    assert features.value_score == 1.0
    assert features.type_score == 1.0


def test_pair_feature_type_mismatch_lowers_type_score() -> None:
    features = MappingPairFeatureService().build(
        make_candidate(source_name="budget_amount", value="not numeric", inferred_type="string"),
        make_field("budget_amount", "number"),
        MappingTemplate(
            template_id="procurement_doc_base_v1",
            schema_id="procurement_doc",
            name="Procurement",
            version="1.0.0",
            aliases={},
        ),
    )

    assert features.type_score < 0.5
    assert features.value_score < 0.5


def test_pair_feature_metadata_source_quality() -> None:
    features = MappingPairFeatureService().build(
        make_candidate(
            source_name="source_url",
            source_path="$.metadata.source_url",
            value="https://example.test/source",
            source_blocks=[],
            evidence_type="metadata",
        ),
        make_field("source"),
        MappingTemplate(
            template_id="policy_doc_base_v1",
            schema_id="policy_doc",
            name="Policy",
            version="1.0.0",
            aliases={"source": ["source_url"]},
        ),
    )

    assert features.path_score == 1.0
    assert features.context_score == 0.75
    assert features.source_quality_score == 0.85
