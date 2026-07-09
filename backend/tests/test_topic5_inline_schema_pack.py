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

    schema = json.loads((pack_dir / "target_schema.json").read_text(encoding="utf-8"))
    assert schema["schema_id"] == "announcement_doc"
    assert schema["schema_id"] not in {
        "policy_doc",
        "meeting_doc",
        "procurement_doc",
        "contract_doc",
        "general_doc",
    }


def test_topic5_inline_request_fixture_uses_schema_pack_assets():
    request_path = ROOT / "examples" / "topic5_inline" / "announcement_convert_request.json"

    payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert payload["uir"]["doc_id"] == "uir_announcement_001"
    assert payload["target_schema"]["schema_id"] == "announcement_doc"
    assert payload["mapping_template"]["schema_id"] == "announcement_doc"
    assert payload["metadata_template"]["template_id"] == "announcement_doc_base_v1"
    assert payload["content_organization"]
    assert payload["options"]["no_code_schema_pack_onboarding"] is True
