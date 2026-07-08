from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_general(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_process_test",
            "metadata": {"domain": "general_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_arrow_process_sentence_emits_process_steps() -> None:
    candidates = CandidateService().extract_candidates(
        "task_general_process",
        make_general(
            [
                {
                    "block_id": "process",
                    "type": "paragraph",
                    "text": "办理流程：网上申请→受理→审核→办结。",
                },
            ]
        ),
    )

    process = next(item for item in candidates if item.display_name == "process_steps")
    assert process.source_name == "办理流程"
    assert process.target_hints == ["process_steps"]
