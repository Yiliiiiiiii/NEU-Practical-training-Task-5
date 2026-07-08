from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"


def make_general() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_conditions_ranking_test",
            "metadata": {"domain": "general_doc", "title": "办事指南", "content": "正文"},
            "blocks": [
                {"block_id": "material", "type": "paragraph", "text": "申请材料：身份证、申请表。"},
                {
                    "block_id": "condition",
                    "type": "paragraph",
                    "text": "申请条件：申请单位须依法登记并信用良好。",
                },
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def test_application_conditions_prefers_condition_label_over_material_list() -> None:
    uir = make_general()
    candidates = CandidateService().extract_candidates("task_general_conditions", uir)
    schema = SchemaService(PRODUCTION_LIKE_DIR / "schemas").load_schema("general_doc")
    template = TemplateService(PRODUCTION_LIKE_DIR / "mapping_templates").load_template(
        "general_doc_base_v1"
    )
    report = MappingService().map_fields(
        "task_general_conditions",
        uir,
        schema,
        template,
        candidates,
    )

    mapping = next(
        item
        for item in report.mappings
        if item["target_field_id"] == "application_conditions"
    )
    assert mapping["source_field_name"] == "申请条件"
