from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_measures_test",
            "metadata": {"domain": "policy_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_policy_measure_section_extracts_only_section_body() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_measures",
        make_policy(
            [
                {"block_id": "heading", "type": "heading", "text": "支持措施"},
                {"block_id": "m1", "type": "paragraph", "text": "一、给予研发补贴。"},
                {"block_id": "m2", "type": "paragraph", "text": "二、支持公共服务平台建设。"},
                {"block_id": "next", "type": "heading", "text": "申报材料"},
                {"block_id": "material", "type": "paragraph", "text": "提交营业执照。"},
            ]
        ),
    )

    measures = next(item for item in candidates if item.display_name == "policy_measures")
    assert measures.source_name == "支持措施"
    assert measures.source_blocks == ["heading", "m1", "m2"]
    assert "提交营业执照" not in measures.value_sample


def test_policy_measure_chapter_heading_uses_gold_section_name() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_measure_chapter",
        make_policy(
            [
                {"block_id": "heading", "type": "heading", "text": "第一章 补贴范围和标准"},
                {
                    "block_id": "scope",
                    "type": "paragraph",
                    "text": "第一条 补贴范围。在京个人消费者购买家电产品给予补贴。",
                },
                {
                    "block_id": "standard",
                    "type": "paragraph",
                    "text": "第二条 补贴标准。最终销售价格的15%。",
                },
                {"block_id": "next", "type": "heading", "text": "第二章 补贴方式及资格设置"},
            ]
        ),
    )

    measures = next(item for item in candidates if item.display_name == "policy_measures")
    assert measures.source_name == "补贴范围和标准"
    assert measures.source_blocks == ["heading", "scope", "standard"]
    assert "第二章" not in measures.value_sample


def test_policy_measure_inline_numbered_section_keeps_section_label() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_inline_measure",
        make_policy(
            [
                {"block_id": "heading", "type": "paragraph", "text": "二、免征增值税的项目"},
                {
                    "block_id": "body",
                    "type": "paragraph",
                    "text": "（一）自2026年1月1日起，下列项目免征增值税。",
                },
                {"block_id": "next", "type": "paragraph", "text": "三、适用简易计税方法的项目"},
            ]
        ),
    )

    measures = next(item for item in candidates if item.display_name == "policy_measures")
    assert measures.source_name == "免征增值税项目"
    assert measures.source_blocks == ["heading", "body"]


def test_policy_measure_support_content_and_revision_terms() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_support_revision_measure",
        make_policy(
            [
                {
                    "block_id": "support",
                    "type": "paragraph",
                    "text": "二、支持内容及标准 （一）支持平台企业发挥赋能带动作用。",
                },
                {"block_id": "next", "type": "paragraph", "text": "三、支持条件"},
                {
                    "block_id": "revision_intro",
                    "type": "paragraph",
                    "text": "现对《管理办法》部分条款予以修订，具体如下：",
                },
                {
                    "block_id": "revision_body",
                    "type": "paragraph",
                    "text": "一、将第四条第二项修订为“安排年度项目支出预算”。",
                },
            ]
        ),
    )

    names = {
        item.source_name for item in candidates if "policy_measures" in item.target_hints
    }
    assert "支持内容及标准" in names
    assert "修订条款" in names
