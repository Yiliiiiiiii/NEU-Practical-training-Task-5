from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_date_role_test",
            "metadata": {"domain": "policy_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_valid_until_is_distinct_from_submission_deadline() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_valid_until",
        make_policy(
            [
                {
                    "block_id": "valid",
                    "type": "paragraph",
                    "text": "本政策有效期至2027年12月31日。",
                },
                {
                    "block_id": "deadline",
                    "type": "paragraph",
                    "text": "申报截止日期为2026年3月1日。",
                },
            ]
        ),
    )

    valid_until = next(item for item in candidates if item.display_name == "valid_until")
    assert valid_until.value_sample == "2027年12月31日"
    assert valid_until.target_hints == ["valid_until"]
    assert not any(
        item.display_name == "valid_until" and item.source_blocks == ["deadline"]
        for item in candidates
    )
