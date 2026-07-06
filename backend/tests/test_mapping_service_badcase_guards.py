import pytest

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.mapping_service import MappingService

FORBIDDEN_PAIRS = [
    ("成文日期", "publish_date"),
    ("发布日期", "effective_date"),
    ("retrieved_at", "effective_date"),
    ("主持人", "attendees"),
    ("联系人", "attendees"),
    ("联系人", "service_object"),
    ("承办单位", "issuer"),
    ("解读机构", "issuer"),
    ("预算金额", "award_amount"),
    ("控制价", "award_amount"),
]


def make_uir() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc-guard",
            "metadata": {},
            "blocks": [
                {"block_id": "source", "type": "paragraph", "text": "source evidence"}
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


@pytest.mark.parametrize(("source_label", "target_field"), FORBIDDEN_PAIRS)
def test_builtin_forbidden_pairs_are_blocked_without_runtime_badcases(
    source_label: str,
    target_field: str,
) -> None:
    schema = TargetSchema(
        schema_id="guard_schema",
        name="Guard schema",
        version="1.0.0",
        fields=[
            TargetField(
                field_id=target_field,
                name=target_field,
                display_name=target_field,
                type="number" if target_field == "award_amount" else "string",
            )
        ],
    )
    template = MappingTemplate(
        template_id="guard_template",
        schema_id="guard_schema",
        name="Guard template",
        version="1.0.0",
        aliases={target_field: [source_label]},
    )
    candidate = FieldCandidate(
        candidate_id="guard-candidate",
        task_id="task-guard",
        doc_id="doc-guard",
        source_path="$.blocks.source.text",
        source_name=source_label,
        display_name=source_label,
        value_sample="2025-06-01" if "date" in target_field else "示例值",
        inferred_type="number" if target_field == "award_amount" else "string",
        source_blocks=["source"],
        confidence=0.95,
        evidence=["extracted from key_value"],
        confidence_hint=0.95,
        evidence_type="key_value",
    )

    report = MappingService().map_fields(
        "task-guard",
        make_uir(),
        schema,
        template,
        [candidate],
    )

    assert report.mappings == []
    assert len(report.review_required_items) == 1
    blocked = report.review_required_items[0]
    assert blocked["status"] == "blocked"
    assert blocked["badcase_filter"]["blocked"] is True
    assert "forbidden_pair" in blocked["risk_flags"]
    assert blocked["source_path"] == "$.blocks.source.text"
