from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def manifest_payload() -> dict:
    return {
        "contract_version": "1.0",
        "schema_pack_id": "announcement_doc",
        "schema_pack_version": "1.0.0",
        "display_name": "Announcement Document",
        "description": "Announcement conversion configuration.",
        "status": "example",
        "owner": "course-team",
        "compatibility": {
            "min_agent_version": "1.0.0",
            "max_agent_version": None,
            "input_uir_version": "1.0",
            "package_contract_version": "1.1",
        },
        "assets": {
            "target_schema": "target_schema.json",
            "metadata_template": "metadata_template.json",
            "mapping_rules": "mapping_rules.yaml",
            "content_org": "content_org.yaml",
            "output_assertions": "output_assertions.yaml",
            "router_rules": "router_rules.yaml",
        },
        "execution": {
            "default_mapping_mode": "global_assignment",
            "allow_llm_fallback": False,
            "include_assertion_report_in_package": False,
        },
        "supported_input": {
            "normalized_uir_required": True,
            "source_formats": ["standard_uir"],
            "languages": ["zh-CN", "en-US"],
        },
        "claim_boundary": {
            "benchmark_scope": True,
            "production_ready": False,
            "notes": "Benchmark example only.",
        },
    }


def assertion_payload(assertions: list[dict] | None = None) -> dict:
    return {
        "contract_version": "1.0",
        "schema_id": "announcement_doc",
        "assertion_set_version": "1.0.0",
        "defaults": {"severity": "error", "missing_optional_field": "skip"},
        "assertions": assertions
        or [
            {
                "assertion_id": "title_non_empty",
                "path": "$.data.title",
                "operator": "non_empty",
                "severity": "error",
                "message": "Title must not be empty.",
            }
        ],
    }


def write_schema_pack(root: Path, *, include_assertions: bool = True) -> Path:
    pack_dir = root / "examples" / "announcement_doc"
    pack_dir.mkdir(parents=True)
    manifest = manifest_payload()
    manifest["assets"]["target_schema"] = "custom-schema.json"
    if not include_assertions:
        manifest["assets"]["output_assertions"] = None
    (pack_dir / "schema_pack.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (pack_dir / "custom-schema.json").write_text(
        json.dumps({"schema_id": "announcement_doc", "fields": []}),
        encoding="utf-8",
    )
    (pack_dir / "target_schema.json").write_text(
        json.dumps({"schema_id": "wrong_guessed_file", "fields": []}),
        encoding="utf-8",
    )
    (pack_dir / "metadata_template.json").write_text(
        json.dumps(
            {
                "template_id": "announcement_doc_base_v1",
                "schema_id": "announcement_doc",
                "version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    mapping_rules = {
        "schema_id": "announcement_doc",
        "template_id": "announcement_doc_base_v1",
        "version": "1.0.0",
        "aliases": {"title": ["title"]},
    }
    (pack_dir / "mapping_rules.yaml").write_text(
        yaml.safe_dump(mapping_rules, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (pack_dir / "content_org.yaml").write_text(
        yaml.safe_dump({"chunk_strategy": "source_block_aware"}),
        encoding="utf-8",
    )
    router_rules = {
        "schema_id": "announcement_doc",
        "template_id": "announcement_doc_base_v1",
        "keywords": ["announcement"],
        "field_labels": ["title"],
    }
    (pack_dir / "router_rules.yaml").write_text(
        yaml.safe_dump(router_rules, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    if include_assertions:
        (pack_dir / "output_assertions.yaml").write_text(
            yaml.safe_dump(assertion_payload(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    return pack_dir


def test_schema_pack_manifest_accepts_valid_strict_contract() -> None:
    from app.schemas.schema_pack_contract import SchemaPackManifest

    manifest = SchemaPackManifest.model_validate(manifest_payload())

    assert manifest.schema_pack_id == "announcement_doc"
    assert manifest.assets.output_assertions == "output_assertions.yaml"


@pytest.mark.parametrize("version", ["1", "1.0", "v1.0.0", "1.0.0.0"])
def test_schema_pack_manifest_rejects_invalid_semver(version: str) -> None:
    from app.schemas.schema_pack_contract import SchemaPackManifest

    payload = manifest_payload()
    payload["schema_pack_version"] = version

    with pytest.raises(ValidationError, match="semantic version"):
        SchemaPackManifest.model_validate(payload)


def test_schema_pack_manifest_rejects_unknown_field() -> None:
    from app.schemas.schema_pack_contract import SchemaPackManifest

    payload = manifest_payload()
    payload["quality_score"] = 0.9

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SchemaPackManifest.model_validate(payload)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../target_schema.json",
        "/tmp/target_schema.json",
        "C:\\tmp\\target_schema.json",
        "C:target_schema.json",
        "\\target_schema.json",
    ],
)
def test_schema_pack_manifest_rejects_unsafe_asset_path(unsafe_path: str) -> None:
    from app.schemas.schema_pack_contract import SchemaPackManifest

    payload = manifest_payload()
    payload["assets"]["target_schema"] = unsafe_path

    with pytest.raises(ValidationError, match="relative path inside the SchemaPack"):
        SchemaPackManifest.model_validate(payload)


def test_conversion_assertion_config_accepts_valid_definition() -> None:
    from app.schemas.conversion_assertions import ConversionAssertionConfig

    config = ConversionAssertionConfig.model_validate(assertion_payload())

    assert config.assertions[0].assertion_id == "title_non_empty"


def test_conversion_assertion_config_rejects_duplicate_ids() -> None:
    from app.schemas.conversion_assertions import ConversionAssertionConfig

    definition = assertion_payload()["assertions"][0]

    with pytest.raises(ValidationError, match="assertion_id must be unique"):
        ConversionAssertionConfig.model_validate(assertion_payload([definition, definition]))


@pytest.mark.parametrize(
    ("definition", "message"),
    [
        (
            {
                "assertion_id": "unknown_operator",
                "path": "$.data.title",
                "operator": "semantic_quality",
            },
            "Input should be",
        ),
        (
            {
                "assertion_id": "missing_type",
                "path": "$.data.title",
                "operator": "type_is",
            },
            "type_is requires parameters.expected",
        ),
        (
            {
                "assertion_id": "invalid_path",
                "path": "$.data[*]",
                "operator": "exists",
            },
            "unsupported JSON path syntax",
        ),
        (
            {
                "assertion_id": "invalid_regex",
                "path": "$.data.title",
                "operator": "regex_match",
                "parameters": {"pattern": "[", "mode": "search"},
            },
            "invalid regular expression",
        ),
        (
            {
                "assertion_id": "invalid_date_format",
                "path": "$.data.publish_date",
                "operator": "date_format",
                "parameters": {"formats": ["%Q"]},
            },
            "invalid strptime format",
        ),
        (
            {
                "assertion_id": "invalid_number_bound",
                "path": "$.data.count",
                "operator": "number_range",
                "parameters": {"min": "0"},
            },
            "number_range bounds must be finite numbers",
        ),
        (
            {
                "assertion_id": "invalid_length_bound",
                "path": "$.data.title",
                "operator": "text_length",
                "parameters": {"min": 1.5},
            },
            "text_length bounds must be non-negative integers",
        ),
        (
            {
                "assertion_id": "invalid_regex_mode_type",
                "path": "$.data.title",
                "operator": "regex_match",
                "parameters": {"pattern": "title", "mode": []},
            },
            "regex_match parameters.mode is unsupported",
        ),
        (
            {
                "assertion_id": "unknown_severity",
                "path": "$.data.title",
                "operator": "exists",
                "severity": "review",
            },
            "Input should be 'error' or 'warning'",
        ),
    ],
)
def test_conversion_assertion_config_rejects_invalid_definition(
    definition: dict,
    message: str,
) -> None:
    from app.schemas.conversion_assertions import ConversionAssertionConfig

    with pytest.raises(ValidationError, match=message):
        ConversionAssertionConfig.model_validate(assertion_payload([definition]))


def test_conversion_assertion_report_has_no_quality_or_route_fields() -> None:
    from app.schemas.conversion_assertion_report import ConversionAssertionReport

    fields = set(ConversionAssertionReport.model_fields)

    assert "quality_score" not in fields
    assert "quality_grade" not in fields
    assert "route_recommendation" not in fields


def test_committed_contract_json_schemas_match_runtime_models() -> None:
    from app.schemas.conversion_assertions import ConversionAssertionConfig
    from app.schemas.schema_pack_contract import SchemaPackManifest

    expected_manifest = SchemaPackManifest.model_json_schema()
    expected_manifest["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected_assertions = ConversionAssertionConfig.model_json_schema()
    expected_assertions["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    manifest_schema = json.loads(
        (ROOT / "schema_packs" / "schema_pack_contract.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assertions_schema = json.loads(
        (ROOT / "schema_packs" / "output_assertions_contract.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest_schema == expected_manifest
    assert assertions_schema == expected_assertions


def test_schema_pack_service_loads_assets_only_from_manifest_references(tmp_path) -> None:
    from app.services.schema_pack_service import SchemaPackService

    write_schema_pack(tmp_path)
    service = SchemaPackService(tmp_path)

    manifest = service.load_manifest("announcement_doc")
    target_schema = service.load_target_schema("announcement_doc")
    metadata_template = service.load_metadata_template("announcement_doc")
    mapping_rules = service.load_mapping_rules("announcement_doc")
    content_org = service.load_content_org("announcement_doc")
    assertions = service.load_output_assertions("announcement_doc")
    router_rules = service.load_router_rules("announcement_doc")

    assert manifest.schema_pack_version == "1.0.0"
    assert target_schema["schema_id"] == "announcement_doc"
    assert metadata_template["template_id"] == "announcement_doc_base_v1"
    assert mapping_rules["aliases"]["title"] == ["title"]
    assert content_org["chunk_strategy"] == "source_block_aware"
    assert assertions is not None
    assert assertions.schema_id == "announcement_doc"
    assert router_rules["keywords"] == ["announcement"]


def test_schema_pack_service_returns_none_when_assertions_are_absent(tmp_path) -> None:
    from app.services.schema_pack_service import SchemaPackService

    write_schema_pack(tmp_path, include_assertions=False)

    assertions = SchemaPackService(tmp_path).load_output_assertions("announcement_doc")

    assert assertions is None


def test_schema_pack_service_rejects_incompatible_uir_before_execution() -> None:
    from app.services.schema_pack_service import SchemaPackService

    with pytest.raises(ValueError, match="input_uir_version"):
        SchemaPackService(ROOT / "schema_packs").validate_for_execution(
            "announcement_doc",
            input_uir_version="2.0",
        )


def test_schema_pack_service_reports_missing_manifest_asset(tmp_path) -> None:
    from app.services.schema_pack_service import SchemaPackService

    pack_dir = write_schema_pack(tmp_path)
    (pack_dir / "custom-schema.json").unlink()

    with pytest.raises(FileNotFoundError, match="custom-schema.json"):
        SchemaPackService(tmp_path).load_target_schema("announcement_doc")


def test_schema_pack_service_router_registry_uses_manifest_assets(tmp_path) -> None:
    from app.services.schema_pack_service import SchemaPackService

    write_schema_pack(tmp_path)

    registry = SchemaPackService(tmp_path).load_router_rules()

    assert registry["announcement_doc"]["source"] == "schema_pack_router_rules"
    assert registry["announcement_doc"]["keywords"] == ["announcement"]


def test_schema_pack_service_router_registry_ignores_pack_without_manifest(
    tmp_path,
) -> None:
    from app.services.schema_pack_service import SchemaPackService

    legacy_dir = tmp_path / "examples" / "legacy_doc"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "router_rules.yaml").write_text(
        yaml.safe_dump({"schema_id": "legacy_doc", "keywords": ["legacy"]}),
        encoding="utf-8",
    )

    registry = SchemaPackService(tmp_path).load_router_rules()

    assert registry == {}
