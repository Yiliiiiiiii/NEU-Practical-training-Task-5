from copy import deepcopy

from app.schemas.external_uir import AdapterReport
from app.schemas.uir import UIRDocument
from app.services.schema_router_service import SchemaRouterService


def make_uir(doc_id: str, text: str) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": doc_id,
            "source": {"source_type": "external_uir", "source_name": "topic11"},
            "metadata": {"title": text},
            "blocks": [
                {
                    "block_id": "b001",
                    "type": "paragraph",
                    "text": text,
                    "attributes": {},
                }
            ],
            "assets": [],
        }
    )


def test_routes_procurement_doc() -> None:
    decision = SchemaRouterService().route(
        make_uir("p1", "采购招标中标公告 项目编号 ABC 中标供应商 某公司 中标金额 100万元")
    )

    assert decision.selected_schema_id == "procurement_doc"
    assert decision.selected_template_id == "procurement_doc_base_v1"
    assert decision.confidence >= 0.75
    assert decision.review_required is False


def test_routes_policy_doc() -> None:
    decision = SchemaRouterService().route(
        make_uir("policy1", "政策通知 实施方案 发布机关 成文日期 发布日期 有效期")
    )

    assert decision.selected_schema_id == "policy_doc"
    assert decision.selected_template_id == "policy_doc_base_v1"


def test_routes_meeting_doc() -> None:
    decision = SchemaRouterService().route(
        make_uir("meeting1", "会议纪要 主持人 参会人员 议题 审议 会议时间")
    )

    assert decision.selected_schema_id == "meeting_doc"
    assert decision.selected_template_id == "meeting_doc_base_v1"


def test_routes_general_doc() -> None:
    decision = SchemaRouterService().route(
        make_uir("general1", "服务指南 办事指南 申请条件 办理流程 材料清单 服务对象 联系方式")
    )

    assert decision.selected_schema_id == "general_doc"
    assert decision.selected_template_id == "general_doc_base_v1"


def test_routes_contract_doc() -> None:
    decision = SchemaRouterService().route(
        make_uir("contract1", "合同协议 甲方 乙方 金额 履约 签订日期 有效期")
    )

    assert decision.selected_schema_id == "contract_doc"
    assert decision.selected_template_id == "contract_doc_base_v1"


def test_low_confidence_requires_review() -> None:
    decision = SchemaRouterService().route(make_uir("unknown1", "普通说明文本，没有明确业务关键词"))

    assert decision.selected_schema_id is None
    assert decision.selected_template_id is None
    assert decision.confidence < 0.5
    assert decision.review_required is True


def test_alternatives_are_sorted_by_confidence() -> None:
    decision = SchemaRouterService().route(
        make_uir("mixed1", "采购通知 中标金额 发布机关 办理流程")
    )

    confidences = [item["confidence"] for item in decision.alternatives]
    assert confidences == sorted(confidences, reverse=True)


def test_router_does_not_mutate_uir() -> None:
    uir = make_uir("stable1", "合同协议 甲方 乙方 金额")
    before = deepcopy(uir.model_dump(mode="json"))

    SchemaRouterService().route(uir)

    assert uir.model_dump(mode="json") == before


def test_router_v2_returns_structured_candidates_and_evidence() -> None:
    decision = SchemaRouterService().route(
        make_uir(
            "procurement-v2",
            "\u91c7\u8d2d\u4e2d\u6807\u516c\u544a "
            "\u4f9b\u5e94\u5546 \u91c7\u8d2d\u4eba "
            "\u9879\u76ee\u7f16\u53f7 \u4e2d\u6807\u91d1\u989d",
        )
    )

    assert decision.route_version == "2.0"
    assert decision.decision_reason
    assert decision.candidates[0].schema_id == "procurement_doc"
    assert decision.candidates[0].reasons
    assert decision.candidates[0].evidence
    assert all(item.matched_schema == "procurement_doc" for item in decision.candidates[0].evidence)
    assert {"metadata", "keyword"} <= {
        item.evidence_type for item in decision.candidates[0].evidence
    }


def test_router_v2_marks_unsafe_procurement_semantics_as_risk() -> None:
    decision = SchemaRouterService().route(
        make_uir(
            "procurement-risk",
            "\u91c7\u8d2d \u62db\u6807 \u4f9b\u5e94\u5546 "
            "\u91c7\u8d2d\u4eba \u4ee3\u7406\u673a\u6784 "
            "\u9884\u7b97\u91d1\u989d \u63a7\u5236\u4ef7",
        )
    )

    candidate = next(
        item for item in decision.candidates if item.schema_id == "procurement_doc"
    )
    assert "budget_amount_not_award_amount" in candidate.risk_flags
    assert "control_price_not_award_amount" in candidate.risk_flags


def test_adapter_route_hint_is_evidence_but_does_not_force_auto_route() -> None:
    adapter_report = AdapterReport(
        adapter_id="section_tree",
        adapter_version="section-tree-adapter-v1",
        source_system="topic11",
        external_doc_id="hint-only",
        generated_doc_id="hint-only",
        status="passed",
        trace_items=[],
        raw_payload_hash="sha256:test",
        route_hints=["meeting_doc"],
    )

    decision = SchemaRouterService().route(
        make_uir("hint-only", "\u666e\u901a\u6587\u672c"),
        adapter_report=adapter_report,
    )

    meeting = next(item for item in decision.candidates if item.schema_id == "meeting_doc")
    assert any(item.evidence_type == "adapter_hint" for item in meeting.evidence)
    assert decision.review_required is True
    assert decision.selected_schema_id is None
