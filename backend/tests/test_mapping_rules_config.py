from __future__ import annotations

from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from tests.topic5_helpers import announcement_mapping_template, announcement_schema


def test_mapping_service_records_configured_negative_pairs():
    schema = TargetSchema.model_validate(announcement_schema())
    template = MappingTemplate.model_validate(announcement_mapping_template())
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "negative_pair",
            "metadata": {"抓取时间": "2026-07-10"},
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )
    candidates = [
        FieldCandidate(
            candidate_id="cand_retrieved",
            task_id="task_negative",
            doc_id="negative_pair",
            source_name="抓取时间",
            source_path="$.metadata.抓取时间",
            value_sample="2026-07-10",
            inferred_type="date",
            confidence=0.8,
            evidence=["test"],
            source_blocks=[],
        )
    ]

    report = MappingService().map_fields(
        task_id="task_negative",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={
            "negative_pairs": [
                {
                    "source_pattern": "抓取时间|retrieved_at",
                    "target_field_id": "publish_date",
                    "reason": "网页抓取时间不是发布日期",
                    "severity": "block",
                }
            ]
        },
    )

    blocked = next(
        item
        for item in report.review_required_items
        if item["target_field_id"] == "publish_date"
    )
    assert blocked["status"] == "blocked"
    assert "configured_negative_pair" in blocked["risk_flags"]
    assert blocked["badcase_filter"]["blocked"] is True
    assert blocked["badcase_filter"]["source"] == "configured_rules"
    assert blocked["badcase_filter"]["reason"] == "网页抓取时间不是发布日期"


def test_mapping_service_uses_inline_alias_and_regex_rules():
    schema = TargetSchema.model_validate(announcement_schema())
    template = MappingTemplate.model_validate(announcement_mapping_template())
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "inline_rules",
            "metadata": {"document_title": "关于开展系统维护的公告"},
            "blocks": [
                {"block_id": "b1", "type": "paragraph", "text": "发布日期：2026-07-09"},
            ],
            "assets": [],
            "normalization_records": [],
        }
    )
    candidates = CandidateService().extract_candidates(
        "task_inline_rules",
        uir,
        enable_legacy_domain_rules=False,
    )

    report = MappingService().map_fields(
        task_id="task_inline_rules",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={"thresholds": {"auto_accept": 0.82, "review_required": 0.62}},
    )

    by_target = {mapping["target_field_id"]: mapping for mapping in report.mappings}
    assert by_target["title"]["method"] == "alias"
    assert by_target["publish_date"]["method"] == "regex"
    assert by_target["publish_date"]["value_sample"] == "2026-07-09"
    assert report.summary["thresholds"] == {"auto_accept": 0.82, "review_required": 0.62}
