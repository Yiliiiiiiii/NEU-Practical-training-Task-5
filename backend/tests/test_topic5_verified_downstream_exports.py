from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from test_downstream_exports import load_script, write_full_package


def _rehash(package: Path, name: str) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256((package / name).read_bytes()).hexdigest()
    for item in manifest["files"]:
        if item["path"] == name:
            item["sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_business_json_is_deterministic_and_preserves_contract_metadata(
    tmp_path: Path,
) -> None:
    exporter = load_script("export_business_json")
    package = write_full_package(tmp_path)
    chunks_path = package / "chunks.jsonl"
    rows = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["source_links"] = [
        {"block_id": "b1", "source_path": "$.blocks.b1.text"}
    ]
    rows[0]["entity_tags"] = [
        {
            "entity_id": "机构-一",
            "entity_type": "organization",
            "source_block_ids": ["b1"],
        }
    ]
    chunks_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    _rehash(package, "chunks.jsonl")

    first = tmp_path / "business-1.json"
    second = tmp_path / "business-2.json"
    result = exporter.export_business_json(package, first)
    exporter.export_business_json(package, second)
    payload = json.loads(first.read_text(encoding="utf-8"))

    assert first.read_bytes() == second.read_bytes()
    assert result["contract_pass"] is True
    assert payload["schema_id"] == "policy_doc"
    assert payload["schema_version"] == "1.0.0"
    assert payload["fields"]["body"]["scope"]
    assert payload["source_links"][0]["block_id"] == "b1"
    assert payload["entity_tags"][0]["entity_id"] == "机构-一"


def test_csv_reports_nested_fields_instead_of_silently_flattening(tmp_path: Path) -> None:
    exporter = load_script("export_structured_csv")
    package = write_full_package(tmp_path)
    content_path = package / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    content["items"] = [{"name": "nested"}]
    content_path.write_text(json.dumps(content), encoding="utf-8")
    _rehash(package, "content.json")

    result = exporter.export_structured_csv(package, tmp_path / "fields.csv")

    assert "items" in result["unsupported_nested_fields"]
    assert result["nested_field_behavior"] == "serialized_as_canonical_json"


@pytest.mark.parametrize("failure", ["unverified", "checksum"])
def test_all_exporters_reject_unverified_or_checksum_invalid_packages(
    tmp_path: Path, failure: str
) -> None:
    package = write_full_package(tmp_path)
    if failure == "unverified":
        (package / "verifier_report.json").write_text(
            json.dumps({"passed": False}), encoding="utf-8"
        )
    else:
        (package / "content.json").write_text("{}", encoding="utf-8")
    calls = [
        ("export_business_json", "export_business_json", "business.json"),
        ("export_structured_csv", "export_structured_csv", "business.csv"),
        ("export_rag_corpus", "export_rag_corpus", "rag.jsonl"),
        ("export_training_corpus", "export_training_corpus", "training.jsonl"),
    ]
    for module_name, function_name, output_name in calls:
        module = load_script(module_name)
        with pytest.raises((ValueError, SystemExit)):
            getattr(module, function_name)(package, tmp_path / output_name)


def test_training_export_rejects_missing_chunk_source(tmp_path: Path) -> None:
    exporter = load_script("export_training_corpus")
    package = write_full_package(tmp_path, linked=False)

    with pytest.raises(ValueError, match="missing source links"):
        exporter.export_training_corpus(package, tmp_path / "training.jsonl")


def test_zip_reader_rejects_path_traversal(tmp_path: Path) -> None:
    consumption = load_script("package_consumption")
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="unsafe ZIP entry"):
        with consumption.resolved_package_dir(archive):
            pass

    assert not (tmp_path / "outside.txt").exists()
