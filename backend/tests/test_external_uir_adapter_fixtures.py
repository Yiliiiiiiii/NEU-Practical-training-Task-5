import json
from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.external_uir_adapter_service import ExternalUIRAdapterService

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "examples" / "external_uir"
EXPECTED = FIXTURES / "expected"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_adapter_contract_covers_at_least_twelve_fixtures() -> None:
    rows = read_jsonl(EXPECTED / "adapter_expected.jsonl")
    fixtures = {
        path.relative_to(FIXTURES).as_posix()
        for path in FIXTURES.rglob("*.json")
        if "expected" not in path.parts and "converted" not in path.parts
    }

    assert len(rows) >= 12
    assert {row["fixture"] for row in rows} == fixtures


def test_all_adapter_fixtures_convert_and_validate() -> None:
    service = ExternalUIRAdapterService()
    for expected in read_jsonl(EXPECTED / "adapter_expected.jsonl"):
        payload = read_json(FIXTURES / expected["fixture"])

        uir, report = service.adapt_from_dict(payload, source_system="quality-polish")

        UIRDocument.model_validate(uir.model_dump(mode="json"))
        assert report.adapter_id == expected["expected_adapter_id"]
        assert len(uir.blocks) >= expected["expected_min_blocks"]
        assert report.trace_coverage >= expected["expected_trace_coverage_min"]
        assert report.llm_auto_accepted_count == 0
        if expected["expected_has_tables"]:
            assert any(
                block.type == "table" and isinstance(block.attributes.get("rows"), list)
                for block in uir.blocks
            )


def test_missing_and_noisy_fixtures_produce_review_warnings() -> None:
    service = ExternalUIRAdapterService()
    for relative in (
        "dialect_a_block_list/sample_policy_missing_fields_external.json",
        "dialect_a_block_list/sample_general_noisy_external.json",
    ):
        payload = read_json(FIXTURES / relative)

        _uir, report = service.adapt_from_dict(
            payload,
            source_system="quality-polish",
        )

        assert report.status == "review_required"
        assert report.warning_count > 0
        assert report.warnings
