import json
from pathlib import Path

from app.services.external_uir_adapter_service import ExternalUIRAdapterService

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples" / "external_uir"
TRACE_EXPECTED = FIXTURES / "expected" / "trace_expected.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_expanded_fixtures_expose_complete_trace_contract() -> None:
    service = ExternalUIRAdapterService()
    for expected in read_jsonl(TRACE_EXPECTED):
        payload = json.loads(
            (FIXTURES / expected["fixture"]).read_text(encoding="utf-8")
        )

        _uir, report = service.adapt_from_dict(
            payload,
            source_system="quality-polish",
        )

        assert report.trace_coverage >= expected["min_trace_coverage"]
        assert report.trace_items
        for item in report.trace_items:
            dumped = item.model_dump(mode="json")
            assert set(expected["required_trace_fields"]) <= set(dumped)
            assert dumped["external_path"]
            assert dumped["target_block_id"]
            assert dumped["conversion_rule"]


def test_nested_sections_keep_external_child_paths() -> None:
    payload = json.loads(
        (
            FIXTURES
            / "dialect_b_section_tree"
            / "sample_meeting_nested_sections_external.json"
        ).read_text(encoding="utf-8")
    )

    uir, report = ExternalUIRAdapterService().adapt_from_dict(
        payload,
        source_system="quality-polish",
    )

    child_paths = [
        item.external_path
        for item in report.trace_items
        if ".children[" in item.external_path
    ]
    assert child_paths
    assert any(
        ".children[" in str(block.attributes.get("external_path", ""))
        for block in uir.blocks
    )
