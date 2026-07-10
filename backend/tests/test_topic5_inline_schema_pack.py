from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_announcement_schema_pack_exists_as_no_code_example():
    pack_dir = ROOT / "schema_packs" / "examples" / "announcement_doc"

    assert (pack_dir / "target_schema.json").is_file()
    assert (pack_dir / "metadata_template.json").is_file()
    assert (pack_dir / "mapping_rules.yaml").is_file()
    assert (pack_dir / "content_org.yaml").is_file()
    assert (pack_dir / "router_rules.yaml").is_file()
    assert (pack_dir / "schema_pack.yaml").is_file()
    assert (pack_dir / "output_assertions.yaml").is_file()
    assert (pack_dir / "examples" / "example_001_uir.json").is_file()
    assert (pack_dir / "examples" / "example_001_request.json").is_file()
    assert (pack_dir / "examples" / "example_001_expected_content.json").is_file()
    assert (pack_dir / "examples" / "example_001_expected_assertions.json").is_file()
    assert (pack_dir / "badcases" / "badcase_001_uir.json").is_file()
    assert (pack_dir / "badcases" / "badcase_001_expected_assertions.json").is_file()
    assert (pack_dir / "badcases" / "negative_pairs.jsonl").is_file()

    schema = json.loads((pack_dir / "target_schema.json").read_text(encoding="utf-8"))
    assert schema["schema_id"] == "announcement_doc"
    assert schema["schema_id"] not in {
        "policy_doc",
        "meeting_doc",
        "procurement_doc",
        "contract_doc",
        "general_doc",
    }


def test_event_notice_schema_pack_has_phase3_contract_fixtures():
    pack_dir = ROOT / "schema_packs" / "examples" / "event_notice_doc"

    required = [
        "schema_pack.yaml",
        "target_schema.json",
        "metadata_template.json",
        "mapping_rules.yaml",
        "content_org.yaml",
        "output_assertions.yaml",
        "router_rules.yaml",
        "examples/example_001_uir.json",
        "examples/example_001_request.json",
        "examples/example_001_expected_content.json",
        "examples/example_001_expected_assertions.json",
        "badcases/badcase_001_uir.json",
        "badcases/badcase_001_expected_assertions.json",
        "badcases/negative_pairs.jsonl",
    ]

    assert all((pack_dir / relative_path).is_file() for relative_path in required)


def test_topic5_inline_request_fixture_uses_schema_pack_assets():
    request_path = ROOT / "examples" / "topic5_inline" / "announcement_convert_request.json"

    payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert payload["uir"]["doc_id"] == "uir_announcement_001"
    assert payload["target_schema"]["schema_id"] == "announcement_doc"
    assert payload["mapping_rules"]["schema_id"] == "announcement_doc"
    assert "mapping_template" not in payload
    assert payload["metadata_template"]["template_id"] == "announcement_doc_base_v1"
    assert payload["content_organization"]
    assert payload["options"]["no_code_schema_pack_onboarding"] is True
