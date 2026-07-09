from __future__ import annotations

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.mapping_repair_service import MappingRepairService


def make_uir() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc-repair",
            "metadata": {"domain": "event_notice_doc"},
            "blocks": [{"block_id": "b1", "type": "paragraph", "text": "title: Repair Notice"}],
            "assets": [],
            "normalization_records": [],
        }
    )


def make_schema() -> TargetSchema:
    return TargetSchema(
        schema_id="event_notice_doc",
        name="Event",
        version="1.0.0",
        fields=[
            TargetField(
                field_id="title",
                name="title",
                display_name="title",
                type="string",
                required=True,
                aliases=["title"],
            )
        ],
    )


def make_template() -> MappingTemplate:
    return MappingTemplate(
        template_id="event_notice_doc_base_v1",
        schema_id="event_notice_doc",
        name="Event",
        version="1.0.0",
        aliases={"title": ["title"]},
    )


def make_candidate(source_name: str, *, target_hint: str = "title") -> FieldCandidate:
    return FieldCandidate(
        candidate_id=f"cand-{source_name}",
        task_id="task-repair",
        doc_id="doc-repair",
        source_path="$.blocks.b1.text",
        source_name=source_name,
        display_name=source_name,
        value_sample="Repair Notice",
        inferred_type="string",
        source_blocks=["b1"],
        confidence=0.9,
        evidence=["extracted from key_value"],
        evidence_type="key_value",
        target_hints=[target_hint],
        confidence_hint=0.9,
    )


def missing_report() -> MappingReport:
    return MappingReport(
        task_id="task-repair",
        schema_id="event_notice_doc",
        summary={
            "total_target_fields": 1,
            "mapped_count": 0,
            "accepted_count": 0,
            "review_required_count": 0,
            "required_unmapped_count": 1,
        },
        mappings=[],
        review_required_items=[],
        unmapped=[
            {
                "target_field_id": "title",
                "target_field_name": "title",
                "required": True,
                "status": "failed",
            }
        ],
    )


def test_mapping_repair_fills_required_missing_with_safe_candidate() -> None:
    repaired, repair_report = MappingRepairService().repair(
        task_id="task-repair",
        uir=make_uir(),
        schema=make_schema(),
        template=make_template(),
        candidates=[make_candidate("title")],
        mapping_report=missing_report(),
        options={"enable_mapping_repair": True},
    )

    assert repair_report["enabled"] is True
    assert repair_report["repaired_fields"] == ["title"]
    assert repaired.summary["required_unmapped_count"] == 0
    assert repaired.mappings[0]["target_field_id"] == "title"


def test_mapping_repair_never_accepts_negative_pair_candidate() -> None:
    repaired, repair_report = MappingRepairService().repair(
        task_id="task-repair",
        uir=make_uir(),
        schema=make_schema(),
        template=make_template(),
        candidates=[make_candidate("publish date")],
        mapping_report=missing_report(),
        options={
            "enable_mapping_repair": True,
            "negative_pairs": [
                {
                    "schema_id": "event_notice_doc",
                    "source_pattern": "publish date",
                    "target_field_id": "title",
                    "reason": "publish date is not title",
                    "severity": "block",
                }
            ],
        },
    )

    assert repaired.mappings == []
    assert repaired.summary["required_unmapped_count"] == 1
    assert repair_report["blocked_candidates"][0]["reason"] == "publish date is not title"
