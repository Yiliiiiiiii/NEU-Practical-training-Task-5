import json
from pathlib import Path

import pytest

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE = ROOT / "examples" / "production_like"


def make_meeting(text: str) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "strict-meeting",
            "metadata": {
                "domain": "meeting_doc",
                "title": "常务会议纪要",
                "source_url": "https://example.gov.cn/meeting",
            },
            "blocks": [
                {"block_id": "title", "type": "title", "text": "常务会议纪要"},
                {"block_id": "opening", "type": "paragraph", "text": text},
                {"block_id": "body", "type": "paragraph", "text": "会议研究有关事项。"},
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


@pytest.mark.parametrize(
    ("text", "date_name", "number_name", "chair_name"),
    [
        (
            "202 6 年 1 月 7 日，县长马建国主持召开县人民政府2026年第1次常务会议。",
            "2026年1月7日",
            "第1次",
            "马建国主持",
        ),
        (
            "202 6 年 1 月 15 日上午，区政府党组书记、区长于占江主持召开"
            "区人民政府2026年第1次常务会议。",
            "2026年1月15日",
            "第1次",
            "于占江主持",
        ),
        (
            "2026年3月6日下午，市委副书记、市长沈晶在市政府501会议室主持召开市政府第64次常务会议。",
            "2026年3月6日",
            "第64次",
            "沈晶主持",
        ),
    ],
)
def test_meeting_opening_facts_keep_semantic_labels_and_distinct_trace_paths(
    text: str,
    date_name: str,
    number_name: str,
    chair_name: str,
) -> None:
    uir = make_meeting(text)

    candidates = CandidateService().extract_candidates("task_strict_meeting", uir)
    expected_names = {
        "meeting_date": date_name,
        "meeting_number": number_name,
        "chairperson": chair_name,
    }
    selected = {
        display_name: next(
            item
            for item in candidates
            if item.display_name == display_name
            and item.source_name == expected_source_name
        )
        for display_name, expected_source_name in expected_names.items()
    }

    assert selected["meeting_date"].source_name == date_name
    assert selected["meeting_number"].source_name == number_name
    assert selected["chairperson"].source_name == chair_name
    assert len({item.source_path for item in selected.values()}) == 3
    assert all(item.source_blocks == ["opening"] for item in selected.values())

    schema = SchemaService(PRODUCTION_LIKE / "schemas").load_schema("meeting_doc")
    template = TemplateService(PRODUCTION_LIKE / "mapping_templates").load_template(
        "meeting_doc_base_v1"
    )
    report = MappingService().map_fields(
        "task_strict_meeting",
        uir,
        schema,
        template,
        candidates,
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["meeting_date"]["source_field_name"] == date_name
    assert mappings["meeting_number"]["source_field_name"] == number_name
    assert mappings["chairperson"]["source_field_name"] == chair_name
    assert mappings["meeting_date"]["value_sample"] == date_name
    assert mappings["meeting_number"]["value_sample"] == number_name
    assert mappings["chairperson"]["value_sample"] == chair_name.removesuffix("主持")
    assert all(
        mappings[field]["status"] == "accepted"
        for field in ("meeting_date", "meeting_number", "chairperson")
    )


def test_meeting_host_is_never_repurposed_as_attendees() -> None:
    uir = make_meeting(
        "2026年3月6日，市委副书记、市长沈晶主持召开市政府第64次常务会议。"
    )
    candidates = CandidateService().extract_candidates("task_host_safety", uir)
    schema = SchemaService(PRODUCTION_LIKE / "schemas").load_schema("meeting_doc")
    template = TemplateService(PRODUCTION_LIKE / "mapping_templates").load_template(
        "meeting_doc_base_v1"
    )

    report = MappingService().map_fields(
        "task_host_safety",
        uir,
        schema,
        template,
        candidates,
        options={
            "badcases": [
                {
                    "source_field": "沈晶主持",
                    "forbidden_target_fields": ["attendees"],
                }
            ]
        },
    )

    assert not any(
        item["target_field_id"] == "attendees"
        and item["source_field_name"] == "沈晶主持"
        and item["status"] == "accepted"
        for item in report.mappings
    )


def test_real_world_policy_fixture_keeps_written_date_out_of_publish_date() -> None:
    payload = json.loads(
        (
            ROOT
            / "examples"
            / "real_world"
            / "uir"
            / "policy"
            / "real_policy_006_technology_incubator_rules.json"
        ).read_text(encoding="utf-8")
    )
    uir = UIRDocument.model_validate(payload)

    candidates = CandidateService().extract_candidates("task_written_date", uir)

    assert any(
        item.display_name == "issuer"
        and item.value_sample == "工业和信息化部"
        for item in candidates
    )
    assert not any(
        item.display_name == "publish_date"
        and item.value_sample in {"2025-06-07", "2025年6月7日"}
        for item in candidates
    )


def test_policy_title_and_official_url_emit_safe_required_candidates() -> None:
    payload = json.loads(
        (
            ROOT
            / "examples"
            / "real_world"
            / "uir"
            / "policy"
            / "real_policy_007_one_thing_list.json"
        ).read_text(encoding="utf-8")
    )
    uir = UIRDocument.model_validate(payload)

    candidates = CandidateService().extract_candidates("task_policy_title_issuer", uir)

    issuer = next(item for item in candidates if item.display_name == "issuer")
    assert issuer.source_name == "国务院办公厅"
    assert issuer.value_sample == "国务院办公厅"
    assert issuer.source_path == "$.metadata.title#issuer"


def test_cac_official_url_date_is_publish_date() -> None:
    payload = json.loads(
        (
            ROOT
            / "examples"
            / "real_world"
            / "uir"
            / "policy"
            / "real_policy_013_minor_platform_rules.json"
        ).read_text(encoding="utf-8")
    )
    uir = UIRDocument.model_validate(payload)

    candidates = CandidateService().extract_candidates("task_cac_publish_date", uir)

    publish_date = next(
        item for item in candidates if item.display_name == "publish_date"
    )
    assert publish_date.source_name == "2026-02-28"
    assert publish_date.value_sample == "2026-02-28"
    assert publish_date.source_path == "$.metadata.source_url#publish_date"


def test_technical_metadata_never_becomes_mapping_candidates() -> None:
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "technical-metadata",
            "metadata": {
                "domain": "general_doc",
                "title": "服务指南",
                "retrieved_at": "2026-07-05T10:00:00+00:00",
                "extraction_version": "0.1.0",
                "extracted_block_count": 99,
                "page_count": 3,
                "page_text_lengths": [100, 200, 300],
                "source_sha256": "a" * 64,
                "source_format": "pdf",
                "extraction_method": "pymupdf_text",
                "extraction_truncated": False,
                "language": "zh-CN",
            },
            "blocks": [
                {"block_id": "body", "type": "paragraph", "text": "办事正文。"},
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    candidates = CandidateService().extract_candidates("task_control_metadata", uir)
    names = {item.source_name for item in candidates}

    assert names.isdisjoint(
        {
                "extraction_version",
            "extracted_block_count",
            "page_count",
            "page_text_lengths",
            "source_sha256",
            "source_format",
            "extraction_method",
            "extraction_truncated",
            "language",
        }
    )
    assert "retrieved_at" in names
