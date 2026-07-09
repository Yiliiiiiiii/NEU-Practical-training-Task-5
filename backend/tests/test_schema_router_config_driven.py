from __future__ import annotations

from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.schema_router_service import SchemaRouterService

ROOT = Path(__file__).resolve().parents[2]


def test_router_loads_announcement_doc_from_schema_pack_rules():
    from app.services.schema_pack_service import SchemaPackService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "announcement_route",
            "metadata": {"title": "系统维护公告"},
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "公告 发布单位 发布日期 正文",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )

    service = SchemaRouterService(
        schema_pack_service=SchemaPackService(ROOT / "schema_packs")
    )
    decision = service.route(uir)

    announcement = next(
        item for item in decision.candidates if item.schema_id == "announcement_doc"
    )
    assert announcement.template_id == "announcement_doc_base_v1"
    assert announcement.source == "schema_pack_router_rules"
    assert any(
        evidence.matched_schema == "announcement_doc"
        and evidence.evidence_type in {"keyword", "field_hint"}
        for evidence in announcement.evidence
    )
