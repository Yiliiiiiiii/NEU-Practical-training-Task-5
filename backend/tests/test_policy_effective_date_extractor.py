from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_effective_test",
            "metadata": {"domain": "policy_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_effective_date_supports_execute_and_effective_phrases() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_effective",
        make_policy(
            [
                {
                    "block_id": "effective",
                    "type": "paragraph",
                    "text": "本办法自2026年7月1日起执行。",
                }
            ]
        ),
    )

    effective = next(item for item in candidates if item.display_name == "effective_date")
    assert effective.value_sample == "2026 年 7 月 1 日"
    assert effective.source_name == "自2026年7月1日起执行"
    assert effective.target_hints == ["effective_date"]


def test_relative_effective_date_is_review_candidate() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_relative_effective",
        make_policy(
            [
                {
                    "block_id": "relative",
                    "type": "paragraph",
                    "text": "本通知自发布之日起生效。",
                }
            ]
        ),
    )

    effective = next(item for item in candidates if item.display_name == "effective_date")
    assert effective.source_name == "自发布之日起生效"
    assert effective.value_sample == "自发布之日起生效"
    assert effective.target_hints == ["effective_date"]
    assert "relative_effective_date_requires_review" in effective.quality_flags


def test_valid_until_open_ended_funding_phrase_is_review_candidate() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_open_valid_until",
        make_policy(
            [
                {
                    "block_id": "valid_until",
                    "type": "paragraph",
                    "text": "本实施细则于2月9日生效，实施至补贴资金使用完毕截止。",
                }
            ]
        ),
    )

    valid_until = next(item for item in candidates if item.display_name == "valid_until")
    assert valid_until.source_name == "实施至补贴资金使用完毕截止"
    assert valid_until.value_sample == "实施至补贴资金使用完毕截止"
    assert valid_until.target_hints == ["valid_until"]
    assert "open_ended_valid_until_requires_review" in valid_until.quality_flags


def test_effective_period_and_partial_effective_phrase_are_candidates() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_effective_period",
        make_policy(
            [
                {
                    "block_id": "period",
                    "type": "paragraph",
                    "text": "自2026年1月1日至2027年12月31日，小规模纳税人发生应税交易。",
                },
                {
                    "block_id": "partial",
                    "type": "paragraph",
                    "text": "本实施细则于2月9日生效，实施至补贴资金使用完毕截止。",
                },
            ]
        ),
    )

    period = next(
        item for item in candidates if item.source_name == "自2026年1月1日至2027年12月31日"
    )
    partial = next(item for item in candidates if item.source_name == "2月9日生效")
    assert period.target_hints == ["effective_date"]
    assert period.value_sample == "自2026年1月1日至2027年12月31日"
    assert partial.target_hints == ["effective_date"]
    assert partial.value_sample == "2月9日生效"
