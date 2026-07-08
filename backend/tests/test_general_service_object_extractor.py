from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_general(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_service_object_test",
            "metadata": {"domain": "general_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_application_object_label_emits_service_object() -> None:
    candidates = CandidateService().extract_candidates(
        "task_general_service_object",
        make_general(
            [
                {
                    "block_id": "object",
                    "type": "paragraph",
                    "text": "申请对象：符合条件的企业法人。",
                },
            ]
        ),
    )

    service_object = next(item for item in candidates if item.display_name == "service_object")
    assert service_object.source_name == "申请对象"
    assert service_object.value_sample == "符合条件的企业法人。"
