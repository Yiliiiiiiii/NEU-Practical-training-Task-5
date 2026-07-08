from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService


def make_policy(blocks: list[dict[str, Any]]):
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_audience_test",
            "metadata": {"domain": "policy_doc"},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def test_explicit_support_object_label_is_low_risk_target_audience() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_audience",
        make_policy(
            [
                {
                    "block_id": "audience",
                    "type": "paragraph",
                    "text": "支持对象：在京个人消费者和中小企业。",
                }
            ]
        ),
    )

    audience = next(item for item in candidates if item.display_name == "target_audience")
    assert audience.source_name == "支持对象"
    assert audience.target_hints == ["target_audience"]
    assert audience.quality_flags == []


def test_notice_addressee_stays_review_required_for_target_audience() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_notice_audience",
        make_policy(
            [
                {
                    "block_id": "addressee",
                    "type": "paragraph",
                    "text": "各有关单位：请认真贯彻执行。",
                }
            ]
        ),
    )

    audience = next(item for item in candidates if item.display_name == "target_audience")
    assert audience.source_name == "各有关单位"
    assert "medium_risk_notice_addressee" in audience.quality_flags


def test_policy_audience_from_subsidy_scope_sentence() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_scope_audience",
        make_policy(
            [
                {
                    "block_id": "scope",
                    "type": "paragraph",
                    "text": "第一条 补贴范围。对在京个人消费者购买1级能效家电产品给予补贴。",
                }
            ]
        ),
    )

    audience = next(item for item in candidates if item.display_name == "target_audience")
    assert audience.source_name == "在京个人消费者"
    assert audience.value_sample == "在京个人消费者"
    assert audience.target_hints == ["target_audience"]


def test_policy_audience_from_long_subsidy_scope_and_mixed_addressee() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_long_scope_audience",
        make_policy(
            [
                {
                    "block_id": "addressee",
                    "type": "paragraph",
                    "text": "各区商务局、北京经济技术开发区商务金融局、各有关单位：",
                },
                {
                    "block_id": "scope",
                    "type": "paragraph",
                    "text": (
                        "第一条 补贴范围。按照全国统一的品类和标准，对在京个人消费者购买"
                        "1级能效或水效标准的冰箱、洗衣机、电视、空调、热水器、电脑6类家电产品，"
                        "以及单件销售价格不超过6000元的手机、平板、智能手表4类数码和智能产品给予补贴。"
                    ),
                },
                {
                    "block_id": "county",
                    "type": "paragraph",
                    "text": "各乡、镇人民政府，各街道办事处，县直有关单位：",
                },
            ]
        ),
    )

    names = {
        item.source_name for item in candidates if "target_audience" in item.target_hints
    }
    assert {"各有关单位", "在京个人消费者", "各乡镇人民政府等"} <= names
