import pytest

from app.schemas.uir import UIRDocument
from app.services.external_uir_adapter_service import ExternalUIRAdapterService


def block_list_payload() -> dict:
    return {
        "id": "ext_proc_001",
        "title": "某采购项目中标公告",
        "url": "https://example.gov/procurement/001",
        "chunks": [
            {"id": "c1", "type": "title", "text": "某采购项目中标公告"},
            {"id": "c2", "type": "paragraph", "text": "项目编号：ABC-001"},
            {
                "id": "c3",
                "type": "table",
                "rows": [["中标供应商", "某某公司"], ["中标金额", "100万元"]],
            },
        ],
    }


def section_tree_payload() -> dict:
    return {
        "document": {
            "docNo": "ext_meeting_001",
            "name": "某市政府常务会议纪要",
            "source": {"url": "https://example.gov/meeting/001"},
            "sections": [
                {
                    "heading": "会议概况",
                    "paragraphs": ["会议时间：2026年6月30日。主持人：张三。"],
                    "children": [
                        {
                            "heading": "审议事项",
                            "paragraphs": ["会议审议通过了若干事项。"],
                        }
                    ],
                }
            ],
        }
    }


def test_detects_block_list_dialect() -> None:
    service = ExternalUIRAdapterService()

    assert service.detect_dialect(block_list_payload()) == "block_list"


def test_detects_section_tree_dialect() -> None:
    service = ExternalUIRAdapterService()

    assert service.detect_dialect(section_tree_payload()) == "section_tree"


def test_adapts_block_list_to_valid_uir() -> None:
    service = ExternalUIRAdapterService()

    uir, report = service.adapt_from_dict(block_list_payload(), source_system="topic11")

    assert isinstance(uir, UIRDocument)
    assert uir.doc_id == "ext_proc_001"
    assert uir.metadata["title"] == "某采购项目中标公告"
    assert uir.source is not None
    assert uir.source.source_type == "external_uir"
    assert uir.source.source_name == "topic11"
    assert len(uir.blocks) == 3
    assert report.status == "passed"


def test_adapts_section_tree_to_valid_uir() -> None:
    service = ExternalUIRAdapterService()

    uir, report = service.adapt_from_dict(section_tree_payload(), source_system="topic11")

    assert isinstance(uir, UIRDocument)
    assert uir.doc_id == "ext_meeting_001"
    assert uir.metadata["title"] == "某市政府常务会议纪要"
    assert [block.type for block in uir.blocks] == [
        "heading",
        "paragraph",
        "heading",
        "paragraph",
    ]
    assert report.status == "passed"


def test_adapter_report_has_trace_items() -> None:
    service = ExternalUIRAdapterService()

    _, report = service.adapt_from_dict(block_list_payload(), source_system="topic11")

    paths = {(item.external_path, item.canonical_path) for item in report.trace_items}
    assert ("payload.id", "doc_id") in paths
    assert ("payload.chunks[0].text", "blocks[0].text") in paths
    assert all(item.evidence for item in report.trace_items)


def test_table_rows_are_preserved() -> None:
    service = ExternalUIRAdapterService()

    uir, _ = service.adapt_from_dict(block_list_payload(), source_system="topic11")

    assert uir.blocks[2].type == "table"
    assert uir.blocks[2].attributes["rows"] == [
        ["中标供应商", "某某公司"],
        ["中标金额", "100万元"],
    ]


def test_external_path_is_preserved_without_relaxing_source_anchor() -> None:
    service = ExternalUIRAdapterService()

    uir, report = service.adapt_from_dict(block_list_payload(), source_system="topic11")

    assert uir.blocks[0].source_anchor is None
    assert uir.blocks[0].attributes["external_path"] == "payload.chunks[0]"
    assert any(
        item.external_path == "payload.chunks[0].text"
        and item.canonical_path == "blocks[0].text"
        for item in report.trace_items
    )


def test_invalid_external_payload_fails_with_report() -> None:
    service = ExternalUIRAdapterService()

    with pytest.raises(ValueError, match="unsupported external UIR dialect"):
        service.adapt_from_dict({"unexpected": []}, source_system="topic11")


def test_adapter_report_preserves_known_schema_hint_for_router() -> None:
    payload = {
        "id": "hinted_001",
        "title": "Plain document",
        "schema_hint": "meeting_doc",
        "chunks": [{"id": "c1", "type": "paragraph", "text": "Plain text"}],
    }

    _, report = ExternalUIRAdapterService().adapt_from_dict(
        payload,
        source_system="topic11",
    )

    assert report.route_hints == ["meeting_doc"]
