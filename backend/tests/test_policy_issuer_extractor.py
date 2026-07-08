from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_issuer_test",
            "metadata": {"domain": "policy_doc", "doc_type": "policy_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_joint_issuer_label_keeps_source_backed_issuer() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_issuer",
        make_policy(
            [
                {
                    "block_id": "issuer",
                    "type": "paragraph",
                    "text": "联合发布机构：工业和信息化部、国家发展改革委。",
                }
            ]
        ),
    )

    issuer = next(item for item in candidates if item.display_name == "issuer")
    assert issuer.source_name == "联合发布机构"
    assert issuer.value_sample == "工业和信息化部、国家发展改革委"
    assert issuer.source_blocks == ["issuer"]


def test_announcement_header_extracts_issuer_and_document_number() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_header",
        make_policy(
            [
                {
                    "block_id": "header",
                    "type": "paragraph",
                    "text": "财政部 税务总局公告2026年第10号",
                }
            ]
        ),
    )

    issuer = next(item for item in candidates if item.display_name == "issuer")
    number = next(item for item in candidates if item.display_name == "document_number")
    assert issuer.source_name == "财政部 税务总局"
    assert issuer.value_sample == "财政部 税务总局"
    assert number.source_name == "公告2026年第10号"
    assert number.value_sample == "公告2026年第10号"


def test_announcement_header_mapping_prefers_source_backed_issuer_over_alias() -> None:
    from pathlib import Path

    from app.services.mapping_service import MappingService
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    root = Path(__file__).resolve().parents[2]
    uir = make_policy(
        [
            {
                "block_id": "header",
                "type": "paragraph",
                "text": "财政部 税务总局公告2026年第10号",
            }
        ]
    )
    candidates_found = CandidateService().extract_candidates(
        "task_policy_issuer_mapping",
        uir,
    )
    schema = SchemaService(root / "examples" / "production_like" / "schemas").load_schema(
        "policy_doc"
    )
    template = TemplateService(
        root / "examples" / "production_like" / "mapping_templates"
    ).load_template("policy_doc_base_v1")
    report = MappingService().map_fields(
        "task_policy_issuer_mapping",
        uir,
        schema,
        template,
        candidates_found,
    )

    issuer = next(item for item in report.mappings if item["target_field_id"] == "issuer")
    assert issuer["source_field"]["source_name"] == "财政部 税务总局"
