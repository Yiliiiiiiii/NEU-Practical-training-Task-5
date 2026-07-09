from __future__ import annotations

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.global_assignment_mapping_service import GlobalAssignmentMappingService


def make_uir() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc-global",
            "metadata": {"domain": "event_notice_doc"},
            "blocks": [
                {"block_id": "b1", "type": "paragraph", "text": "event time: 2026-07-12 14:00"},
                {"block_id": "b2", "type": "paragraph", "text": "publish date: 2026-07-09"},
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def make_schema(*fields: TargetField) -> TargetSchema:
    return TargetSchema(
        schema_id="event_notice_doc",
        name="Event",
        version="1.0.0",
        fields=list(fields),
    )


def field(field_id: str, field_type: str = "string", *, required: bool = False) -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id.replace("_", " "),
        type=field_type,
        required=required,
        aliases=[field_id.replace("_", " ")],
    )


def template() -> MappingTemplate:
    return MappingTemplate(
        template_id="event_notice_doc_base_v1",
        schema_id="event_notice_doc",
        name="Event",
        version="1.0.0",
        aliases={
            "event_time": ["event time", "start time"],
            "publish_date": ["publish date"],
            "title": ["title"],
        },
    )


def candidate(
    candidate_id: str,
    source_name: str,
    source_path: str,
    value: object,
    *,
    target_hints: list[str] | None = None,
    evidence_type: str = "key_value",
    confidence: float = 0.9,
    source_blocks: list[str] | None = None,
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=candidate_id,
        task_id="task-global",
        doc_id="doc-global",
        source_path=source_path,
        source_name=source_name,
        display_name=source_name,
        value_sample=value,
        inferred_type="datetime" if "time" in source_name else "date",
        source_blocks=source_blocks if source_blocks is not None else ["b1"],
        confidence=confidence,
        evidence=[f"extracted from {evidence_type}"],
        target_hints=target_hints or [],
        evidence_type=evidence_type,
        confidence_hint=confidence,
    )


def test_global_assignment_chooses_best_non_conflicting_pairs() -> None:
    report = GlobalAssignmentMappingService().map_fields(
        task_id="task-global",
        uir=make_uir(),
        schema=make_schema(field("event_time", "datetime"), field("publish_date", "date")),
        template=template(),
        candidates=[
            candidate(
                "publish",
                "publish date",
                "$.blocks.b2.text",
                "2026-07-09",
                target_hints=["publish_date"],
                source_blocks=["b2"],
            ),
            candidate(
                "event",
                "event time",
                "$.blocks.b1.text",
                "2026-07-12 14:00",
                target_hints=["event_time"],
                source_blocks=["b1"],
            ),
        ],
    )

    assert {item["target_field_id"]: item["candidate_id"] for item in report.mappings} == {
        "event_time": "event",
        "publish_date": "publish",
    }
    assert report.summary["mapping_mode"] == "global_assignment"
    assert report.summary["conflict_skipped_count"] >= 0


def test_global_assignment_required_unmapped_fields_are_reported() -> None:
    report = GlobalAssignmentMappingService().map_fields(
        task_id="task-global",
        uir=make_uir(),
        schema=make_schema(field("title", required=True)),
        template=template(),
        candidates=[],
    )

    assert report.mappings == []
    assert report.unmapped[0]["target_field_id"] == "title"
    assert report.summary["required_unmapped_count"] == 1


def test_global_assignment_negative_pair_is_blocked() -> None:
    report = GlobalAssignmentMappingService().map_fields(
        task_id="task-global",
        uir=make_uir(),
        schema=make_schema(field("event_time", "datetime", required=True)),
        template=template(),
        candidates=[
            candidate(
                "publish",
                "publish date",
                "$.blocks.b2.text",
                "2026-07-09",
                target_hints=["event_time"],
                source_blocks=["b2"],
            )
        ],
        options={
            "negative_pairs": [
                {
                    "schema_id": "event_notice_doc",
                    "source_pattern": "publish date",
                    "target_field_id": "event_time",
                    "reason": "publish date is not event time",
                    "severity": "block",
                }
            ]
        },
    )

    assert report.mappings == []
    assert report.review_required_items[0]["status"] == "blocked"
    assert "negative_pair_block" in report.review_required_items[0]["risk_flags"]


def test_global_assignment_review_threshold_creates_review_item() -> None:
    report = GlobalAssignmentMappingService().map_fields(
        task_id="task-global",
        uir=make_uir(),
        schema=make_schema(field("event_time", "datetime")),
        template=template(),
        candidates=[
            candidate(
                "weak",
                "start",
                "$.blocks.b1.text",
                "2026-07-12",
                evidence_type="metadata",
                confidence=0.62,
            )
        ],
        options={"auto_accept_threshold": 0.95, "review_threshold": 0.45},
    )

    assert report.mappings == []
    assert report.review_required_items[0]["target_field_id"] == "event_time"
    assert report.review_required_items[0]["status"] == "review_required"
