from app.adapters.base import AdapterInput
from app.adapters.registry import build_default_registry


def block_list_payload() -> dict:
    return {
        "id": "ext_general_001",
        "title": "Service guide",
        "chunks": [
            {"id": "c1", "type": "title", "text": "Service guide"},
            {"id": "c2", "type": "paragraph", "text": "Application materials"},
        ],
    }


def section_tree_payload() -> dict:
    return {
        "document": {
            "docNo": "ext_meeting_001",
            "name": "Meeting minutes",
            "sections": [{"heading": "Agenda", "paragraphs": ["Reviewed project status"]}],
        }
    }


def test_default_registry_lists_builtin_adapter_capabilities() -> None:
    registry = build_default_registry()

    capabilities = registry.list_capabilities()

    assert [item.adapter_id for item in capabilities] == ["block_list", "section_tree"]
    assert capabilities[0].supported_dialects == ["block-list", "block_list"]
    assert capabilities[1].supports_sections is True
    assert all(item.requires_llm is False for item in capabilities)


def test_registry_selects_explicit_dialect_hint() -> None:
    registry = build_default_registry()

    selected = registry.select_adapter(
        AdapterInput(
            payload=section_tree_payload(),
            source_system="topic11",
            dialect_hint="section_tree",
        )
    )

    assert selected.adapter_id == "section_tree"
    assert selected.confidence == 1.0
    assert selected.review_required is False
    assert selected.alternatives[0].adapter_id == "section_tree"


def test_registry_auto_detects_block_list() -> None:
    registry = build_default_registry()

    selected = registry.select_adapter(
        AdapterInput(payload=block_list_payload(), source_system="topic11")
    )

    assert selected.adapter_id == "block_list"
    assert selected.confidence >= 0.9
    assert selected.review_required is False


def test_registry_marks_unknown_payload_for_review() -> None:
    registry = build_default_registry()

    selected = registry.select_adapter(
        AdapterInput(payload={"unexpected": []}, source_system="topic11")
    )

    assert selected.adapter_id is None
    assert selected.confidence == 0.0
    assert selected.review_required is True
    assert selected.error == "unsupported_dialect"
