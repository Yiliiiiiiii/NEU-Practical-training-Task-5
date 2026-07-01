import json
from pathlib import Path

from test_downstream_exports import load_script, write_full_package, zip_package


def test_contract_passes_complete_package(tmp_path: Path) -> None:
    module = load_script("verify_downstream_contract")
    result = module.verify_package(write_full_package(tmp_path))
    assert result["passed"] is True
    assert result["export_structured_csv_passed"] is True
    assert result["export_rag_corpus_passed"] is True


def test_batch_discovers_named_package_zip(tmp_path: Path) -> None:
    module = load_script("verify_downstream_contract")
    package = write_full_package(tmp_path)
    zip_package(package, tmp_path / "real_policy_001.zip")
    report = module.run_batch(tmp_path)
    assert report["summary"] == {
        "package_count": 1,
        "passed_count": 1,
        "failed_count": 0,
    }


def test_contract_fails_hash_mismatch_missing_artifact_and_empty_chunks(
    tmp_path: Path,
) -> None:
    module = load_script("verify_downstream_contract")
    package = write_full_package(tmp_path)
    (package / "content.json").write_text("{}", encoding="utf-8")
    assert module.verify_package(package)["passed"] is False

    package = write_full_package(tmp_path / "missing")
    (package / "canonical.json").unlink()
    assert module.verify_package(package)["passed"] is False

    package = write_full_package(tmp_path / "empty")
    (package / "chunks.jsonl").write_text("", encoding="utf-8")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = [
        item for item in manifest["files"] if item["path"] != "chunks.jsonl"
    ]
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert module.verify_package(package)["passed"] is False
