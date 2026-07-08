from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_general(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_contact_test",
            "metadata": {"domain": "general_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_service_hotline_emits_contact_candidate() -> None:
    candidates = CandidateService().extract_candidates(
        "task_general_contact",
        make_general(
            [
                {
                    "block_id": "contact",
                    "type": "paragraph",
                    "text": "服务热线：12345、010-87654321",
                },
            ]
        ),
    )

    contact = next(item for item in candidates if item.display_name == "contact")
    assert contact.value_sample == "12345、010-87654321"
    assert contact.target_hints == ["contact"]


def test_garbled_phone_requires_review() -> None:
    candidates = CandidateService().extract_candidates(
        "task_general_bad_contact",
        make_general(
            [
                {"block_id": "contact", "type": "paragraph", "text": "咨询电话：????"},
            ]
        ),
    )

    contact = next(item for item in candidates if item.display_name == "contact")
    assert "medium_risk_garbled_contact" in contact.quality_flags
