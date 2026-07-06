import json
import re
from pathlib import Path

import pytest
from test_downstream_exports import load_script, write_full_package, zip_package

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"


def test_contract_registry_contains_versioned_unique_manifests() -> None:
    paths = sorted(CONTRACTS.glob("*.json"))
    assert len(paths) >= 4
    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in paths
    ]

    contract_ids = [manifest["contract_id"] for manifest in manifests]
    assert len(contract_ids) == len(set(contract_ids))
    for manifest in manifests:
        assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
        assert manifest["artifact_type"] in {"csv", "jsonl", "package"}
        assert manifest.get("required_fields") or manifest.get(
            "required_package_files"
        )


def test_rag_contract_verifies_package_export(tmp_path: Path) -> None:
    module = load_script("consumer_contract")
    result = module.verify_consumer_contract(
        write_full_package(tmp_path),
        CONTRACTS / "rag_corpus_contract_v1.json",
    )

    assert result["passed"] is True
    assert result["contract_id"] == "rag_corpus_contract"
    assert result["record_count"] == 2
    assert result["errors"] == []


def test_contract_reports_missing_required_record_path(tmp_path: Path) -> None:
    module = load_script("consumer_contract")
    contract = tmp_path / "strict.json"
    contract.write_text(
        json.dumps(
            {
                "contract_id": "strict_rag",
                "version": "1.0.0",
                "artifact_type": "jsonl",
                "exporter": "export_rag_corpus",
                "required_fields": ["metadata.not_present"],
            }
        ),
        encoding="utf-8",
    )

    result = module.verify_consumer_contract(
        write_full_package(tmp_path / "input"),
        contract,
    )

    assert result["passed"] is False
    assert "metadata.not_present" in result["errors"][0]


def test_batch_verification_discovers_nested_package_zips(tmp_path: Path) -> None:
    module = load_script("consumer_contract")
    first = write_full_package(tmp_path / "first")
    second = write_full_package(tmp_path / "second")
    zip_package(first, tmp_path / "first.zip")
    nested = tmp_path / "nested"
    nested.mkdir()
    zip_package(second, nested / "second.zip")

    report = module.verify_batch(
        tmp_path,
        CONTRACTS / "training_corpus_contract_v1.json",
    )

    assert report["package_count"] == 2
    assert report["passed_count"] == 2
    assert report["consumer_contract_pass_rate"] == 1.0


@pytest.mark.parametrize(
    "contract_name",
    [
        "rag_corpus_contract_v1.json",
        "training_corpus_contract_v1.json",
        "structured_csv_contract_v1.json",
        "package_contract_v1_1.json",
    ],
)
def test_each_registered_contract_verifies_complete_package(
    tmp_path: Path,
    contract_name: str,
) -> None:
    module = load_script("consumer_contract")
    package = write_full_package(tmp_path)
    (package / "transform_report.json").write_text(
        '{"passed":true}',
        encoding="utf-8",
    )

    result = module.verify_consumer_contract(
        package,
        CONTRACTS / contract_name,
    )

    assert result["passed"] is True, result["errors"]
