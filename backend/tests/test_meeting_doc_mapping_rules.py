from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService
from app.services.transform_service import TransformService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"


def meeting_uir(
    metadata: dict[str, object],
    *,
    block_text: str = "会议围绕重点工作进行讨论。",
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "meeting_mapping_test",
            "metadata": {"domain": "meeting_doc", **metadata},
            "blocks": [
                {
                    "block_id": "meeting_b001",
                    "type": "paragraph",
                    "text": block_text,
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def map_meeting(uir: UIRDocument):
    schema = SchemaService(SCHEMAS_DIR).load_schema("meeting_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "meeting_doc_base_v1",
        "1.0.0",
    )
    candidates = CandidateService().extract_candidates("task_meeting", uir)
    report = MappingService().map_fields(
        task_id="task_meeting",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )
    return schema, template, report


def test_meeting_exact_alias_and_regex_rules_normalize_labeled_date() -> None:
    uir = meeting_uir(
        {
            "meeting_title": "重点项目调度会",
            "content": "会议审议重点项目推进安排。",
            "主持人": "张主任",
            "审议事项": ["项目进度", "风险处置"],
        },
        block_text="会议时间：2026年6月30日",
    )

    schema, template, report = map_meeting(uir)
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["meeting_title"]["method"] == "exact"
    assert mappings["content"]["method"] == "exact"
    assert mappings["chairperson"]["source_field_name"] == "主持人"
    assert mappings["chairperson"]["method"] == "alias"
    assert mappings["agenda_items"]["source_field_name"] == "审议事项"
    assert mappings["meeting_date"]["status"] == "accepted"

    transformed = TransformService().transform(
        task_id="task_meeting",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=report,
    )
    assert transformed.data["meeting_date"] == "2026-06-30"


def test_meeting_date_alias_supports_explicit_call_date() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "会议名称": "专题会议",
                "召开日期": "2026-06-30",
                "会议内容": "形成工作安排。",
            }
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["meeting_date"]["method"] == "alias"
    assert mappings["meeting_date"]["source_field_name"] == "召开日期"


def test_meeting_decision_item_alias_does_not_collide_with_agenda_items() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "专题协调会",
                "meeting_date": "2026-06-30",
                "content": "会议形成明确议定事项。",
                "议定事项": ["同意项目实施方案", "明确责任分工"],
            }
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["decision_items"]["source_field_name"] == "议定事项"
    assert not any(
        item["target_field_id"] == "agenda_items"
        and item["source_field_name"] == "议定事项"
        for item in report.mappings
    )


def test_meeting_long_tail_aliases_map_decisions_and_actions() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "重点工作会议",
                "meeting_date": "2026-06-30",
                "content": "会议形成工作安排。",
                "审议通过": ["项目方案"],
                "责任分工": ["由产业科负责"],
            }
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["decisions"]["source_field_name"] == "审议通过"
    assert mappings["action_items"]["source_field_name"] == "责任分工"


def test_meeting_topics_from_numbered_agenda_headings() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "重点工作会议",
                "meeting_date": "2026-06-30",
                "content": "会议记录正文。",
            },
            block_text="一、研究产业项目推进事项",
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["topics"]["source_field_name"] == "会议内容"
    assert "产业项目推进事项" in mappings["topics"]["value_sample"]


def test_meeting_topics_from_research_and_review_sentences() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "重点工作会议",
                "meeting_date": "2026-06-30",
                "content": "会议记录正文。",
            },
            block_text="会议研究了城市更新项目推进方案。",
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["topics"]["source_field_name"] == "会议内容"
    assert "城市更新项目推进方案" in mappings["topics"]["value_sample"]


def test_meeting_attendees_are_not_topics() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "重点工作会议",
                "meeting_date": "2026-06-30",
                "content": "会议记录正文。",
            },
            block_text="出席人员：张三、李四、王五",
        )
    )

    assert not any(
        item["target_field_id"] == "topics"
        and item["source_field_name"] == "出席人员"
        for item in report.mappings
    )


def test_meeting_action_items_from_responsibility_sentence() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "重点工作会议",
                "meeting_date": "2026-06-30",
                "content": "会议记录正文。",
            },
            block_text="由产业科负责牵头推进项目落地。",
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["action_items"]["source_field_name"] == "责任行动"


def test_meeting_opening_host_is_organizer_review_candidate() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "meeting_title": "常务会议纪要",
                "content": "会议记录正文。",
            },
            block_text="2026年5月20日，区长李明主持召开区政府常务会议。",
        )
    )

    assert any(
        item["target_field_id"] == "organizer"
        and item["source_field_name"] == "李明"
        and item["status"] == "review_required"
        for item in report.review_required_items
    )


def test_meeting_numbers_headers_and_ambiguous_roles_are_not_auto_titles() -> None:
    _, _, report = map_meeting(
        meeting_uir(
            {
                "会议编号": "2026-15",
                "页眉": "市政府办公室",
                "文件编号": "府办会纪〔2026〕15号",
                "召集人": "李主任",
                "召开日期": "2026-06-30",
                "content": "会议记录正文。",
            }
        )
    )

    forbidden_sources = {"会议编号", "页眉", "文件编号"}
    assert not any(
        item["target_field_id"] == "meeting_title"
        and item["source_field_name"] in forbidden_sources
        for item in report.mappings
    )
    assert not any(
        item["source_field_name"] == "召集人"
        and item["target_field_id"] in {"organizer", "chairperson"}
        for item in report.mappings
    )
    assert any(
        item["source_field_name"] == "召集人" and item["status"] == "review_required"
        for item in report.review_required_items
    )
