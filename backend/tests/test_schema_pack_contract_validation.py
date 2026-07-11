from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _copy_pack(tmp_path: Path, schema_pack_id: str = "announcement_doc") -> Path:
    source = ROOT / "schema_packs" / "examples" / schema_pack_id
    pack = tmp_path / schema_pack_id
    shutil.copytree(source, pack)
    return pack


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _run_validator(pack_dir: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_schema_pack.py"), str(pack_dir)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if not completed.stdout.strip():
        return {"status": "crashed", "errors": [completed.stderr]}
    return json.loads(completed.stdout)


def _run_validator_with_out(pack_dir: Path, out_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_schema_pack.py"),
            str(pack_dir),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_validate_announcement_schema_pack_passes():
    result = _run_validator(ROOT / "schema_packs" / "examples" / "announcement_doc")

    assert result["status"] == "passed"
    assert result["errors"] == []


def test_validate_event_notice_schema_pack_passes():
    result = _run_validator(ROOT / "schema_packs" / "examples" / "event_notice_doc")

    assert result["status"] == "passed"
    assert result["errors"] == []


def test_bundled_content_organization_contracts_use_nested_summary_modes():
    for schema_pack_id in ("announcement_doc", "event_notice_doc"):
        content_org = _read_yaml(
            ROOT / "schema_packs" / "examples" / schema_pack_id / "content_org.yaml"
        )

        assert "summary_mode" not in content_org
        assert content_org["summary"]["chunk_mode"] == "deterministic"
        assert content_org["summary"]["document_mode"] == "extractive"
        assert _run_validator(
            ROOT / "schema_packs" / "examples" / schema_pack_id
        )["status"] == "passed"


def test_validate_schema_pack_fails_on_missing_mapping_rules(tmp_path):
    source = ROOT / "schema_packs" / "examples" / "announcement_doc"
    pack = tmp_path / "announcement_doc"
    shutil.copytree(source, pack)
    (pack / "mapping_rules.yaml").unlink()

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "mapping_rules.yaml is missing" in result["errors"]


def test_validate_schema_pack_reports_invalid_negative_pair_regex(tmp_path):
    source = ROOT / "schema_packs" / "examples" / "announcement_doc"
    pack = tmp_path / "announcement_doc"
    shutil.copytree(source, pack)
    mapping_rules_path = pack / "mapping_rules.yaml"
    mapping_rules = mapping_rules_path.read_text(encoding="utf-8")
    invalid_rules, replacement_count = re.subn(
        r"(?m)^  - source_pattern:.*$",
        '  - source_pattern: "["',
        mapping_rules,
        count=1,
    )
    assert replacement_count == 1
    mapping_rules_path.write_text(invalid_rules, encoding="utf-8")

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any(
        "negative_pairs[0].source_pattern is invalid" in item
        for item in result["errors"]
    )


def test_validate_schema_pack_requires_manifest(tmp_path):
    source = ROOT / "schema_packs" / "examples" / "announcement_doc"
    pack = tmp_path / "announcement_doc"
    shutil.copytree(source, pack)
    (pack / "schema_pack.yaml").unlink()

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "schema_pack.yaml is missing" in result["errors"]


def test_validate_schema_pack_cli_writes_json_report(tmp_path):
    pack = ROOT / "schema_packs" / "examples" / "announcement_doc"
    out_path = tmp_path / "contract-report.json"

    completed = _run_validator_with_out(pack, out_path)

    assert completed.returncode == 0
    assert json.loads(out_path.read_text(encoding="utf-8"))["status"] == "passed"


def test_validate_schema_pack_rejects_unsafe_asset_path(tmp_path):
    pack = _copy_pack(tmp_path)
    manifest_path = pack / "schema_pack.yaml"
    manifest = _read_yaml(manifest_path)
    manifest["assets"]["target_schema"] = "../target_schema.json"
    _write_yaml(manifest_path, manifest)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("relative path inside the SchemaPack" in item for item in result["errors"])


def test_validate_schema_pack_rejects_cross_file_schema_id_mismatch(tmp_path):
    pack = _copy_pack(tmp_path)
    target_path = pack / "target_schema.json"
    target = json.loads(target_path.read_text(encoding="utf-8"))
    target["schema_id"] = "wrong_schema"
    target_path.write_text(json.dumps(target), encoding="utf-8")

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "target_schema.json.schema_id does not match schema_pack_id" in result["errors"]


def test_validate_schema_pack_reports_invalid_mapping_regex(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["regex_rules"][0]["pattern"] = "["
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any(
        "mapping_rules.yaml.regex_rules[0].pattern is invalid" in item
        for item in result["errors"]
    )


def test_validate_schema_pack_reports_invalid_output_assertion_regex(tmp_path):
    pack = _copy_pack(tmp_path)
    assertions_path = pack / "output_assertions.yaml"
    assertions = _read_yaml(assertions_path)
    assertions["assertions"].append(
        {
            "assertion_id": "invalid_regex",
            "path": "$.data.title",
            "operator": "regex_match",
            "parameters": {"pattern": "[", "mode": "search"},
        }
    )
    _write_yaml(assertions_path, assertions)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any(
        "output_assertions.yaml" in item and "invalid regular expression" in item
        for item in result["errors"]
    )


def test_validate_schema_pack_rejects_duplicate_assertion_id(tmp_path):
    pack = _copy_pack(tmp_path)
    assertions_path = pack / "output_assertions.yaml"
    assertions = _read_yaml(assertions_path)
    assertions["assertions"].append(dict(assertions["assertions"][0]))
    _write_yaml(assertions_path, assertions)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("assertion_id must be unique" in item for item in result["errors"])


def test_validate_schema_pack_rejects_unknown_assertion_target_field(tmp_path):
    pack = _copy_pack(tmp_path)
    assertions_path = pack / "output_assertions.yaml"
    assertions = _read_yaml(assertions_path)
    assertions["assertions"].append(
        {
            "assertion_id": "unknown_field",
            "path": "$.data.publishDate",
            "operator": "exists",
        }
    )
    _write_yaml(assertions_path, assertions)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any(
        "references unknown target field publishDate" in item
        for item in result["errors"]
    )


def test_validate_schema_pack_rejects_invalid_metadata_template(tmp_path):
    pack = _copy_pack(tmp_path)
    metadata_path = pack / "metadata_template.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("schema_id")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("metadata_template.json is invalid" in item for item in result["errors"])


def test_validate_schema_pack_rejects_invalid_content_organization(tmp_path):
    pack = _copy_pack(tmp_path)
    content_path = pack / "content_org.yaml"
    content = _read_yaml(content_path)
    content["target_tokens"] = 1500
    _write_yaml(content_path, content)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("target_tokens must be between" in item for item in result["errors"])


def test_validate_schema_pack_rejects_invalid_router_structure(tmp_path):
    pack = _copy_pack(tmp_path)
    router_path = pack / "router_rules.yaml"
    router = _read_yaml(router_path)
    router["keywords"] = "announcement"
    _write_yaml(router_path, router)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("keywords must be an array of strings" in item for item in result["errors"])


def test_validate_schema_pack_rejects_invalid_mapping_structure(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["aliases"] = ["title"]
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("mapping_rules.yaml.aliases must be an object" in item for item in result["errors"])


def test_validate_schema_pack_reports_malformed_target_without_crashing(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["regex_rules"][0]["target_field_id"] = ["publish_date"]
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert result["status"] != "crashed"
    assert any("target_field_id is missing" in item for item in result["errors"])


def test_validate_schema_pack_rejects_unknown_mapping_field(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["threshholds"] = {"auto_accept": 0.82}
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "mapping_rules.yaml.threshholds is unsupported" in result["errors"]


def test_validate_schema_pack_rejects_non_numeric_mapping_threshold(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["thresholds"]["auto_accept"] = "not-a-number"
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("must be a finite number" in item for item in result["errors"])


def test_validate_schema_pack_rejects_unknown_mapping_threshold(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["thresholds"]["auto_acceppt"] = 0.82
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert "mapping_rules.yaml.thresholds.auto_acceppt is unsupported" in result["errors"]


def test_validate_schema_pack_rejects_inverted_mapping_thresholds(tmp_path):
    pack = _copy_pack(tmp_path)
    mapping_path = pack / "mapping_rules.yaml"
    mapping = _read_yaml(mapping_path)
    mapping["thresholds"] = {"auto_accept": 0.2, "review_required": 0.9}
    _write_yaml(mapping_path, mapping)

    result = _run_validator(pack)

    assert result["status"] == "failed"
    assert any("review_required cannot exceed" in item for item in result["errors"])
