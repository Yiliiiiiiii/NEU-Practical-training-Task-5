from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]], metadata: dict[str, Any] | None = None):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_extract_test",
            "metadata": {"domain": "policy_doc", **(metadata or {})},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def candidates(blocks: list[dict[str, Any]], metadata: dict[str, Any] | None = None):
    return CandidateService().extract_candidates(
        "task_policy_extract",
        make_policy(blocks, metadata),
    )


def test_explicit_publication_label_emits_publish_date_candidate() -> None:
    found = candidates(
        [
            {
                "block_id": "meta",
                "type": "paragraph",
                "text": "发布时间：2026年2月6日",
            }
        ]
    )

    publish = next(item for item in found if item.display_name == "publish_date")
    assert publish.value_sample == "2026年2月6日"
    assert publish.target_hints == ["publish_date"]
    assert publish.source_blocks == ["meta"]


def test_retrieved_at_metadata_is_forbidden_for_publish_date() -> None:
    found = candidates([], {"retrieved_at": "2026-02-06", "发布时间": "2026-02-01"})

    retrieved = next(item for item in found if item.source_name == "retrieved_at")
    assert "publish_date" not in retrieved.target_hints
    assert "forbidden_publish_date" in retrieved.quality_flags


def test_signature_date_can_be_authoritative_when_no_label_exists() -> None:
    found = candidates(
        [
            {
                "block_id": "signature",
                "type": "paragraph",
                "text": "北京市商务局 2026年2月6日",
            }
        ],
        {"source_url": "https://sw.beijing.gov.cn/zwxx/202602/t20260206_4496652.html"},
    )

    signed = next(item for item in found if item.source_name == "signed date")
    assert signed.value_sample == "2026年2月6日"
    assert signed.target_hints == ["publish_date"]
    assert signed.quality_flags == []


def test_date_revision_history_is_review_candidate_for_publish_date() -> None:
    found = candidates(
        [
            {
                "block_id": "history",
                "type": "paragraph",
                "text": "（1995年10月30日第八届全国人民代表大会常务委员会第十六次会议通过）",
            }
        ]
    )

    reviewed = next(item for item in found if item.source_name == "1995年10月30日通过")
    assert reviewed.value_sample == "1995年10月30日"
    assert reviewed.target_hints == ["publish_date"]
    assert "medium_risk_revision_history_date" in reviewed.quality_flags


def test_issue_date_label_is_review_only_publish_date_candidate() -> None:
    found = candidates(
        [
            {
                "block_id": "issue_date",
                "type": "paragraph",
                "text": "成文日期：2026年2月11日",
            }
        ]
    )

    issue_date = next(item for item in found if item.source_name == "成文日期")
    assert issue_date.value_sample == "2026年2月11日"
    assert issue_date.target_hints == ["publish_date"]
    assert "medium_risk_issue_date_for_publish" in issue_date.quality_flags
