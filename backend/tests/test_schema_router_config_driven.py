from __future__ import annotations

from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.schema_router_service import SchemaRouterService

ROOT = Path(__file__).resolve().parents[2]


def test_router_config_only_mode_uses_announcement_doc_router_rules():
    from app.services.schema_pack_service import SchemaPackService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "announcement_route",
            "metadata": {"title": "系统维护公告 通知"},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "公告 通知 公示 发布单位 发布日期 正文",
                    "attributes": {},
                },
                {
                    "block_id": "b2",
                    "type": "table",
                    "text": "",
                    "attributes": {
                        "rows": [
                            {"field": "公告标题", "value": "系统维护公告"},
                            {"field": "发布单位", "value": "office"},
                            {"field": "发布日期", "value": "2026-07-09"},
                        ]
                    },
                },
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    service = SchemaRouterService(
        schema_pack_service=SchemaPackService(ROOT / "schema_packs"),
        include_builtin_signals=False,
    )
    decision = service.route(uir)

    assert decision.selected_schema_id == "announcement_doc"
    announcement = next(
        item for item in decision.candidates if item.schema_id == "announcement_doc"
    )
    assert announcement.template_id == "announcement_doc_base_v1"
    assert announcement.source == "schema_pack_router_rules"
    assert any(
        evidence.matched_schema == "announcement_doc"
        and evidence.evidence_type in {"keyword", "field_hint", "table_label"}
        for evidence in announcement.evidence
    )


def test_router_config_only_mode_returns_review_when_no_schema_packs(tmp_path):
    from app.services.schema_pack_service import SchemaPackService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "empty_route",
            "metadata": {"title": "unknown"},
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )

    router = SchemaRouterService(
        schema_pack_service=SchemaPackService(tmp_path),
        include_builtin_signals=False,
    )
    decision = router.route(uir)

    assert decision.selected_schema_id is None
    assert decision.review_required is True
    assert decision.confidence == 0.0
    assert decision.reason == "no schema router rules configured"


def test_router_default_mode_keeps_builtin_signals():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "builtin_route",
            "metadata": {"title": "采购中标公告"},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "采购 招标 供应商 采购人 项目编号 中标金额",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    decision = SchemaRouterService().route(uir)

    assert decision.selected_schema_id is not None
