"""Evaluate deterministic exports from verified Topic 5 packages."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from topic5_reliability_common import (
    BACKEND,
    ROOT,
    example_request,
    load_json,
    performance_request,
)

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.services.topic5_conversion_service import Topic5ConversionService  # noqa: E402
from export_business_json import export_business_json  # noqa: E402
from export_rag_corpus import export_rag_corpus  # noqa: E402
from export_structured_csv import export_structured_csv  # noqa: E402
from export_training_corpus import export_training_corpus  # noqa: E402
from package_consumption import PackageReadError  # noqa: E402

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_downstream" / "v1" / "report.json"
ExportFunction = Callable[[Path, Path], dict[str, Any]]


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _add_unicode_entity(payload: dict[str, Any], marker: str) -> None:
    block_id = payload["uir"]["blocks"][0]["block_id"]
    payload["uir"].setdefault("entities", []).append(
        {
            "mention": "\u53ef\u9760\u6027\u529e\u516c\u5ba4",
            "canonical_name": "\u53ef\u9760\u6027\u529e\u516c\u5ba4",
            "entity_type": "organization",
            "normalized_id": f"org:reliability:{marker}",
            "link_status": "linked",
            "confidence": 1.0,
            "source_block_ids": [block_id],
            "source_agent": "downstream-contract-evaluator",
            "evidence": {"marker": marker},
        }
    )
    payload["uir"]["metadata"]["unicode_marker"] = "\u4e0b\u6e38\u9a8c\u8bc1"


def _meeting_request() -> dict[str, Any]:
    payload = {
        "uir": load_json(
            ROOT
            / "examples"
            / "production_like"
            / "uir"
            / "meeting"
            / "meeting_001_standard.json"
        ),
        "target_schema": load_json(
            ROOT / "examples" / "production_like" / "schemas" / "meeting_doc_v1.json"
        ),
        "mapping_rules": load_json(
            ROOT
            / "examples"
            / "production_like"
            / "mapping_templates"
            / "meeting_doc_base_v1.json"
        ),
        "content_organization": example_request()["content_organization"],
        "options": {"enable_llm_fallback": False},
    }
    payload["content_organization"]["summary"] = {
        "chunk_mode": "deterministic",
        "document_mode": "extractive",
    }
    return payload


def _create_package(root: Path, payload: dict[str, Any], marker: str) -> Path:
    payload = copy.deepcopy(payload)
    payload.pop("output_assertions", None)
    _add_unicode_entity(payload, marker)
    response = Topic5ConversionService(
        root, settings=Settings(storage_root=str(root), llm_mode="disabled")
    ).convert(Topic5ConvertRequest.model_validate(payload), create_package=True)
    path = Path(str(response.package_zip_path))
    if not path.is_file() or not response.verifier_report or not response.verifier_report["passed"]:
        raise RuntimeError(f"failed to create verified package for {marker}")
    return path.parent


def _exporters() -> dict[str, ExportFunction]:
    return {
        "business_json": export_business_json,
        "csv": export_structured_csv,
        "rag_jsonl": lambda package, output: export_rag_corpus(
            package, output, fail_on_missing_source_links=True
        ),
        "training_jsonl": export_training_corpus,
    }


def _suffix(name: str) -> str:
    return ".csv" if name == "csv" else ".json" if name == "business_json" else ".jsonl"


def _read_rows(name: str, path: Path) -> list[dict[str, Any]]:
    if name == "business_json":
        return [json.loads(path.read_text(encoding="utf-8"))]
    if name == "csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _preserves_contract(name: str, rows: list[dict[str, Any]]) -> tuple[bool, bool, bool]:
    if name == "business_json":
        row = rows[0]
        versioned = bool(row.get("schema_version") and row.get("template_version"))
        return bool(row.get("source_links")), bool(row.get("entity_tags")), versioned
    if name == "csv":
        row = rows[0]
        return (
            row.get("source_links") not in {None, "", "[]"},
            row.get("entity_tags") not in {None, "", "[]"},
            bool(row.get("schema_version") and row.get("template_version")),
        )
    metadata = rows[0].get("metadata", {}) if rows else {}
    return (
        all(row.get("metadata", {}).get("source_links") for row in rows),
        any(row.get("metadata", {}).get("entity_tags") for row in rows),
        bool(metadata.get("schema_version") and metadata.get("template_version")),
    )


def _rehash(package: Path, filename: str) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256((package / filename).read_bytes()).hexdigest()
    for item in manifest["files"]:
        if item["path"] == filename:
            item["sha256"] = digest
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_evaluation() -> dict[str, Any]:
    with TemporaryDirectory(prefix="topic5-downstream-") as temp_dir:
        root = Path(temp_dir)
        packages = {
            "announcement": _create_package(root, example_request(), "announcement"),
            "event_notice": _create_package(
                root, example_request("event_notice"), "event_notice"
            ),
            "nested_array": _create_package(root, _meeting_request(), "nested_array"),
            "large": _create_package(root, performance_request(100), "large"),
        }
        exporters = _exporters()
        cases: list[dict[str, Any]] = []
        for package_name, package in packages.items():
            content = load_json(package / "content.json")
            nested_present = any(
                isinstance(value, (dict, list))
                for value in content.get("data", {}).values()
            )
            for exporter_name, exporter in exporters.items():
                first = root / "exports" / f"{package_name}-{exporter_name}-1{_suffix(exporter_name)}"
                second = root / "exports" / f"{package_name}-{exporter_name}-2{_suffix(exporter_name)}"
                result = exporter(package, first)
                exporter(package, second)
                rows = _read_rows(exporter_name, first)
                source_ok, entity_ok, version_ok = _preserves_contract(
                    exporter_name, rows
                )
                passed = (
                    result["contract_pass"]
                    and first.read_bytes() == second.read_bytes()
                    and source_ok
                    and entity_ok
                    and version_ok
                )
                cases.append(
                    {
                        "case_id": f"{package_name}:{exporter_name}",
                        "package_type": package_name,
                        "exporter": exporter_name,
                        "deterministic": first.read_bytes() == second.read_bytes(),
                        "source_links_preserved": source_ok,
                        "entity_tags_preserved": entity_ok,
                        "versions_preserved": version_ok,
                        "nested_fields_present": nested_present,
                        "unsupported_nested_fields": result.get(
                            "unsupported_nested_fields", []
                        ),
                        "unicode_preserved": "\u53ef\u9760\u6027\u529e\u516c\u5ba4" in first.read_text(
                            encoding="utf-8-sig"
                        ),
                        "passed": passed,
                    }
                )

        invalid = root / "invalid-checksum"
        shutil.copytree(packages["announcement"], invalid)
        (invalid / "content.json").write_text("{}", encoding="utf-8")
        invalid_rejections = []
        for exporter_name, exporter in exporters.items():
            try:
                exporter(invalid, root / f"invalid-{exporter_name}{_suffix(exporter_name)}")
            except (PackageReadError, SystemExit, ValueError):
                invalid_rejections.append(exporter_name)

        missing = root / "missing-source"
        shutil.copytree(packages["announcement"], missing)
        chunk_path = missing / "chunks.jsonl"
        chunks = [
            json.loads(line)
            for line in chunk_path.read_text(encoding="utf-8").splitlines()
        ]
        for chunk in chunks:
            chunk["source_links"] = []
            chunk["source_block_ids"] = []
        chunk_path.write_text(
            "\n".join(json.dumps(chunk, ensure_ascii=False, sort_keys=True) for chunk in chunks),
            encoding="utf-8",
        )
        _rehash(missing, "chunks.jsonl")
        missing_source_rejections = []
        for exporter_name in ("rag_jsonl", "training_jsonl"):
            try:
                exporters[exporter_name](
                    missing,
                    root / f"missing-{exporter_name}{_suffix(exporter_name)}",
                )
            except (PackageReadError, SystemExit, ValueError):
                missing_source_rejections.append(exporter_name)

    export_passed = sum(case["passed"] for case in cases)
    checks = {
        "verified_package_export_pass_rate": export_passed == len(cases),
        "invalid_package_rejection_rate": len(invalid_rejections) == len(exporters),
        "missing_source_rejection_rate": len(missing_source_rejections) == 2,
        "source_link_preservation": all(
            case["source_links_preserved"] for case in cases
        ),
        "entity_tag_preservation": all(case["entity_tags_preserved"] for case in cases),
        "nested_array_fixture_present": any(
            case["package_type"] == "nested_array" and case["nested_fields_present"]
            for case in cases
        ),
        "unicode_preservation": all(case["unicode_preserved"] for case in cases),
    }
    passed = all(checks.values())
    return {
        "status": "passed" if passed else "failed",
        "dataset_id": "topic5_downstream_contracts",
        "dataset_version": "1.0.0",
        "commit_sha": _git_head(),
        "case_count": len(cases),
        "passed_count": export_passed,
        "verified_package_export_pass_rate": export_passed / len(cases),
        "invalid_package_rejection_rate": len(invalid_rejections) / len(exporters),
        "source_link_preservation_rate": sum(
            case["source_links_preserved"] for case in cases
        )
        / len(cases),
        "invalid_package_export_acceptance": len(exporters) - len(invalid_rejections),
        "checks": checks,
        "failed_conditions": [name for name, value in checks.items() if not value],
        "cases": cases,
        "reproduction_command": "python scripts/eval_downstream_contracts.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_evaluation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
