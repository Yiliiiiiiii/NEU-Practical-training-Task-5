from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE = ROOT / "examples" / "production_like"


def policy_mapping(text: str):
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "strict-policy",
            "metadata": {
                "domain": "policy_doc",
                "title": "管理办法",
                "发文机关": "工业和信息化部",
            },
            "blocks": [
                {"block_id": "body", "type": "paragraph", "text": text},
            ],
            "assets": [],
            "normalization_records": [],
        }
    )
    schema = SchemaService(PRODUCTION_LIKE / "schemas").load_schema("policy_doc")
    template = TemplateService(PRODUCTION_LIKE / "mapping_templates").load_template(
        "policy_doc_base_v1"
    )
    candidates = CandidateService().extract_candidates("task_strict_policy", uir)
    return (
        template,
        MappingService().map_fields(
            "task_strict_policy",
            uir,
            schema,
            template,
            candidates,
        ),
    )


def test_policy_effective_date_regex_accepts_real_world_whitespace() -> None:
    _template, report = policy_mapping("第五十条 本办法自 2026 年 4 月 1 日起施行。")

    effective = next(
        item for item in report.mappings if item["target_field_id"] == "effective_date"
    )
    assert effective["method"] == "regex"
    assert effective["value_sample"] == "2026 年 4 月 1 日"


def test_policy_written_date_is_not_publish_date_alias_or_regex() -> None:
    template, report = policy_mapping("成文日期：2025-06-07")

    assert "成文日期" not in template.aliases["publish_date"]
    assert all(
        "成文日期" not in rule.pattern
        for rule in template.regex_rules
        if rule.target_field_id == "publish_date"
    )
    assert not any(
        item["target_field_id"] == "publish_date"
        and item["value_sample"] == "2025-06-07"
        for item in report.mappings
    )


def test_retrieved_at_is_not_effective_date() -> None:
    _template, report = policy_mapping("本办法适用于相关平台。")

    assert not any(
        item["target_field_id"] == "effective_date"
        and item["source_field_name"] == "retrieved_at"
        and item["status"] == "accepted"
        for item in report.mappings
    )


def test_explicit_attendance_label_maps_attendees_without_host_alias() -> None:
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "strict-meeting-attendees",
            "metadata": {
                "domain": "meeting_doc",
                "meeting_title": "专题会议",
                "content": "会议形成工作安排。",
                "主持人": "张主任",
            },
            "blocks": [
                {
                    "block_id": "attendees",
                    "type": "paragraph",
                    "text": "出 席：李委员、王委员",
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )
    schema = SchemaService(PRODUCTION_LIKE / "schemas").load_schema("meeting_doc")
    template = TemplateService(PRODUCTION_LIKE / "mapping_templates").load_template(
        "meeting_doc_base_v1"
    )
    report = MappingService().map_fields(
        "task_strict_meeting_attendees",
        uir,
        schema,
        template,
        CandidateService().extract_candidates(
            "task_strict_meeting_attendees",
            uir,
        ),
    )

    attendees = next(
        item for item in report.mappings if item["target_field_id"] == "attendees"
    )
    assert attendees["source_field_name"] == "出 席"
    assert not any(
        item["target_field_id"] == "attendees"
        and item["source_field_name"] == "主持人"
        for item in report.mappings
    )
