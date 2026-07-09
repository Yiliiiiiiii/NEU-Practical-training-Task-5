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


def general_uir(
    metadata: dict[str, object],
    *,
    block_text: str = "这是通用文档正文。",
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_mapping_test",
            "metadata": metadata,
            "blocks": [
                {
                    "block_id": "general_b001",
                    "type": "paragraph",
                    "text": block_text,
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def map_general(uir: UIRDocument):
    schema = SchemaService(SCHEMAS_DIR).load_schema("general_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "general_doc_base_v1",
        "1.0.0",
    )
    candidates = CandidateService().extract_candidates("task_general", uir)
    report = MappingService().map_fields(
        task_id="task_general",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )
    return schema, template, report


def test_general_exact_alias_regex_and_enum_rules_map_only_explicit_labels() -> None:
    uir = general_uir(
        {
            "title": "企业服务办事指南",
            "content": "介绍申请条件、材料和办理步骤。",
            "文档类型": "办事指南",
            "服务对象": "本市企业",
        },
        block_text="发布日期：2026年6月30日\n联系电话：010-12345678",
    )

    schema, template, report = map_general(uir)
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["title"]["method"] == "exact"
    assert mappings["content"]["method"] == "exact"
    assert mappings["document_subtype"]["source_field_name"] == "文档类型"
    assert mappings["document_subtype"]["method"] == "alias"
    assert mappings["service_object"]["source_field_name"] == "服务对象"
    assert mappings["published_at"]["method"] == "regex"
    assert mappings["contact"]["method"] == "regex"

    transformed = TransformService().transform(
        task_id="task_general",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=report,
    )
    assert transformed.data["document_subtype"] == "service_guide"
    assert transformed.data["published_at"] == "2026-06-30"
    assert transformed.data["contact"] == "010-12345678"


def test_general_process_and_amount_labels_never_auto_map_to_category() -> None:
    _, _, report = map_general(
        general_uir(
            {
                "title": "项目申报说明",
                "content": "按要求提交材料。",
                "办理流程": ["提交申请", "部门审核"],
                "预算金额": "100万元",
            }
        )
    )

    accepted_category_sources = {
        item["source_field_name"]
        for item in report.mappings
        if item["target_field_id"] == "category"
    }
    assert accepted_category_sources.isdisjoint({"办理流程", "预算金额"})
    assert any(
        item["target_field_id"] == "process_steps"
        and item["source_field_name"] == "办理流程"
        and item["status"] == "accepted"
        for item in report.mappings
    )


def test_general_long_tail_aliases_map_deadline_contact_and_title() -> None:
    _, _, report = map_general(
        general_uir(
            {
                "一级标题": "科技项目申报指南",
                "content": "申报说明。",
                "报名截止": "2026-08-01",
                "邮箱": "service@example.com",
            }
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["title"]["source_field_name"] == "一级标题"
    assert mappings["deadline"]["source_field_name"] == "报名截止"
    assert mappings["contact"]["source_field_name"] == "邮箱"
