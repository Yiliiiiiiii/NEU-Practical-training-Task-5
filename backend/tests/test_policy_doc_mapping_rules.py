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


def policy_uir(
    metadata: dict[str, object],
    *,
    block_text: str = "政策正文。",
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_mapping_test",
            "metadata": metadata,
            "blocks": [
                {
                    "block_id": "policy_b001",
                    "type": "paragraph",
                    "text": block_text,
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def map_policy(uir: UIRDocument):
    schema = SchemaService(SCHEMAS_DIR).load_schema("policy_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "policy_doc_base_v1",
        "1.0.0",
    )
    candidates = CandidateService().extract_candidates("task_policy", uir)
    report = MappingService().map_fields(
        task_id="task_policy",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )
    return schema, template, report


def test_policy_exact_alias_and_regex_rules_map_explicit_policy_labels() -> None:
    uir = policy_uir(
        {
            "title": "促进中小企业发展若干措施",
            "content": "提出融资、服务和人才支持措施。",
            "制定机关": "市发展改革委",
            "政策措施": ["融资支持", "公共服务"],
        },
        block_text="发布日期：2026年6月30日",
    )

    schema, template, report = map_policy(uir)
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["title"]["method"] == "exact"
    assert mappings["content"]["method"] == "exact"
    assert mappings["issuer"]["source_field_name"] == "制定机关"
    assert mappings["issuer"]["method"] == "alias"
    assert mappings["policy_measures"]["source_field_name"] == "政策措施"
    assert mappings["publish_date"]["method"] == "regex"

    transformed = TransformService().transform(
        task_id="task_policy",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=report,
    )
    assert transformed.data["publish_date"] == "2026-06-30"


def test_policy_aliases_support_printing_agency_but_keep_authored_date_for_review() -> None:
    _, _, report = map_policy(
        policy_uir(
            {
                "政策名称": "产业扶持办法",
                "印发机关": "市人民政府办公室",
                "成文日期": "2026-06-30",
                "主要内容": "明确扶持范围。",
            }
        )
    )
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["issuer"]["source_field_name"] == "印发机关"
    assert "publish_date" not in mappings
    assert any(
        item["source_field_name"] == "成文日期"
        and item["target_field_id"] == "publish_date"
        for item in report.review_required_items
    )


def test_policy_interpretation_citation_and_attachment_dates_require_review() -> None:
    _, _, report = map_policy(
        policy_uir(
            {
                "title": "政策解读",
                "issuer": "市政策研究室",
                "content": "解读相关政策。",
                "政策解读页面发布日期": "2026-06-30",
                "引用政策发布日期": "2025-12-01",
                "附件日期": "2026-05-20",
            },
            block_text=(
                "政策解读页面发布日期：2026年6月30日\n"
                "引用政策发布日期：2025年12月1日\n"
                "附件日期：2026年5月20日"
            ),
        )
    )

    ambiguous_sources = {"政策解读页面发布日期", "引用政策发布日期", "附件日期"}
    assert not any(
        item["target_field_id"] == "publish_date"
        and item["source_field_name"] in ambiguous_sources
        for item in report.mappings
    )
    assert any(
        item["target_field_id"] == "publish_date"
        and item["source_field_name"] in ambiguous_sources
        and item["status"] == "review_required"
        for item in report.review_required_items
    )
