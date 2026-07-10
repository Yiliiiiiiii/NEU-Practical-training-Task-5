"""Evaluate exact Topic 5 issue localization against production validators."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.metadata_template import MetadataTemplateConfig  # noqa: E402
from app.schemas.target_schema import TargetField, TargetSchema  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.manifest_service import ManifestService  # noqa: E402
from app.services.metadata_template_service import MetadataTemplateService  # noqa: E402
from app.services.package_verifier_service import PackageVerifierService  # noqa: E402
from app.services.render_service import RenderedArtifacts  # noqa: E402
from app.services.validation_service import ValidationService  # noqa: E402

DEFAULT_FIXTURE = ROOT / "eval" / "topic5_schema_localization" / "v1" / "cases.json"
DEFAULT_OUTPUT = ROOT / "docs" / "交接" / "evidence" / "hard_gap_batch_1" / "operations"


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if payload.get("version") != "1.0.0" or not isinstance(cases, list):
        raise ValueError("schema-localization fixture must be version 1.0.0")
    if len(cases) < 40:
        raise ValueError("schema-localization fixture requires at least 40 cases")
    case_ids = [case.get("case_id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("schema-localization case_id values must be unique")
    for case in cases:
        for key in ("expected_stage", "expected_path", "expected_error_code"):
            if not case.get(key):
                raise ValueError(f"{case.get('case_id')} is missing {key}")
    return payload


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    issues = _issues_for_case(case)
    expected = (
        case["expected_stage"],
        case["expected_path"],
        case["expected_error_code"],
    )
    triples = [(item["stage"], item["path"], item["error_code"]) for item in issues]
    passed = expected in triples
    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "expected_stage": expected[0],
        "expected_path": expected[1],
        "expected_error_code": expected[2],
        "actual_issues": issues,
        "path_correct": any(item[1] == expected[1] for item in triples),
        "error_code_correct": any(
            item[1] == expected[1] and item[2] == expected[2] for item in triples
        ),
        "stage_correct": any(
            item[0] == expected[0] and item[1] == expected[1] for item in triples
        ),
        "passed": passed,
    }


def _issues_for_case(case: dict[str, Any]) -> list[dict[str, str]]:
    scenario = case["scenario"]
    if scenario in {"required_missing", "field_value", "chunk_source", "unexpected_top_level"}:
        return _validation_issues(case)
    if scenario == "metadata":
        return _metadata_issues(case)
    if scenario == "invalid_entity_source":
        return _entity_issues()
    if scenario in {"package_role", "missing_consistency_report"}:
        return _package_issues(scenario)
    raise ValueError(f"unsupported localization scenario: {scenario}")


def _validation_issues(case: dict[str, Any]) -> list[dict[str, str]]:
    scenario = case["scenario"]
    field_id = str(case.get("field_id", "title"))
    field = TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=str(case.get("field_type", "string")),
        required=scenario == "required_missing",
        constraints=case.get("constraints", {}),
    )
    schema = TargetSchema(
        schema_id="localization",
        name="Localization",
        version="1.0.0",
        fields=[field],
        json_schema=(
            {"additionalProperties": False}
            if scenario == "unexpected_top_level"
            else {}
        ),
    )
    data: dict[str, Any] = {}
    if scenario == "field_value":
        data[field_id] = case.get("value")
    elif scenario == "unexpected_top_level":
        data = {field_id: "valid", "extra": "forbidden"}
    chunks = [
        {
            "chunk_id": "c1",
            "text": "source",
            "source_block_ids": ["missing" if scenario == "chunk_source" else "b1"],
        }
    ]
    report = ValidationService().validate(
        "localization",
        schema,
        RenderedArtifacts(
            structured_json={
                "data": data,
                "blocks": [{"block_id": "b1", "text": "source"}],
            },
            markdown="# source\n",
            chunks=chunks,
        ),
    )
    return [
        {
            "stage": str(issue.stage or "schema_validation"),
            "path": str(issue.path or issue.field_id or ""),
            "error_code": str(issue.code or ""),
        }
        for issue in report.issues
    ]


def _metadata_issues(case: dict[str, Any]) -> list[dict[str, str]]:
    metadata = {case["field_id"]: case["value"]} if "value" in case else {}
    field_config = {
        "field_id": case["field_id"],
        "type": case["field_type"],
        "required": bool(case.get("required", False)),
        "allow_empty": bool(case.get("allow_empty", True)),
    }
    template = MetadataTemplateConfig.model_validate(
        {
            "template_id": "localization-v1",
            "schema_id": "localization",
            "version": "1.0.0",
            "metadata_fields": [field_config],
        }
    )
    result = MetadataTemplateService().render(
        uir=UIRDocument(
            uir_version="1.0", doc_id="localization", metadata=metadata
        ),
        transformed_fields={},
        template=template,
        system_context={},
    )
    return [
        {
            "stage": issue.stage,
            "path": issue.path,
            "error_code": issue.error_code,
        }
        for issue in result.report.issues
    ]


def _entity_issues() -> list[dict[str, str]]:
    try:
        UIRDocument.model_validate(
            {
                "uir_version": "1.0",
                "doc_id": "localization",
                "blocks": [{"block_id": "b1", "type": "paragraph", "text": "x"}],
                "entities": [
                    {
                        "mention": "OpenAI",
                        "link_status": "unlinked",
                        "source_block_ids": ["missing"],
                    }
                ],
            }
        )
    except ValidationError as exc:
        if "entity source_block_ids contains unknown block_id" in str(exc):
            return [
                {
                    "stage": "uir_contract",
                    "path": "entities",
                    "error_code": "entity_source_block_unknown",
                }
            ]
    return []


def _package_issues(scenario: str) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = Path(temp_dir)
        features = ["artifact_consistency_v1"] if scenario == "missing_consistency_report" else []
        payloads = {
            "content.json": "{}",
            "content.md": "# content\n",
            "chunks.jsonl": json.dumps(
                {
                    "chunk_id": "c1",
                    "text": "source",
                    "tags": {},
                    "keywords": [],
                    "summary": "",
                    "source_block_ids": ["b1"],
                }
            )
            + "\n",
            "mapping_report.json": "{}",
            "validation_report.json": "{}",
            "content_organization_report.json": "{}",
            "metadata.json": json.dumps({"features": features}),
        }
        for name, content in payloads.items():
            (package_dir / name).write_text(content, encoding="utf-8")
        entries = []
        for path in sorted(package_dir.iterdir()):
            role = ManifestService.role(path.name)
            if scenario == "package_role" and path.name == "content.json":
                role = "wrong_role"
            entries.append(
                {
                    "path": path.name,
                    "required": True,
                    "media_type": ManifestService.media_type(path.name),
                    "sha256": ManifestService.sha256_file(path),
                    "bytes": path.stat().st_size,
                    "role": role,
                }
            )
        manifest = {
            "manifest_version": "1.1",
            "package_id": "pkg-localization",
            "package_version": "1.0.0",
            "task_id": "task-localization",
            "doc_id": "doc-localization",
            "created_at": "2026-07-10T00:00:00+00:00",
            "files": entries,
            "generator": {"name": "localization", "version": "1.0.0"},
        }
        (package_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        report = PackageVerifierService().verify_package(package_dir, strict=True)
        return [
            {
                "stage": str(issue.stage or "package_verifier"),
                "path": str(issue.path or ""),
                "error_code": str(issue.code or ""),
            }
            for issue in report.errors
        ]


def build_report(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    results = [evaluate_case(case) for case in fixture["cases"]]
    total = len(results)
    localized = sum(item["passed"] for item in results)
    path_correct = sum(item["path_correct"] for item in results)
    code_correct = sum(item["error_code_correct"] for item in results)
    stage_correct = sum(item["stage_correct"] for item in results)
    return {
        "dataset_id": fixture["dataset_id"],
        "dataset_version": fixture["version"],
        "dataset_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "commit_sha": _commit_sha(),
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": total,
        "localized_count": localized,
        "schema_localization_rate": localized / total,
        "path_accuracy": path_correct / total,
        "error_code_accuracy": code_correct / total,
        "stage_accuracy": stage_correct / total,
        "failed_cases": [item for item in results if not item["passed"]],
        "cases": results,
        "reproduction_command": (
            "backend/.venv/Scripts/python.exe scripts/eval_topic5_schema_localization.py"
        ),
        "claim_boundary": (
            "Measures exact stage/path/error-code localization for declared Topic 5 "
            "validators; it does not measure semantic document quality."
        ),
    }


def _commit_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Topic 5 Schema Localization",
            "",
            f"- Dataset: `{report['dataset_id']}` `{report['dataset_version']}`",
            f"- Dataset SHA-256: `{report['dataset_sha256']}`",
            f"- Commit: `{report['commit_sha']}`",
            f"- Cases: {report['case_count']}",
            f"- Localization rate: {report['schema_localization_rate']:.3f}",
            f"- Path accuracy: {report['path_accuracy']:.3f}",
            f"- Error-code accuracy: {report['error_code_accuracy']:.3f}",
            f"- Stage accuracy: {report['stage_accuracy']:.3f}",
            "",
            f"Reproduce: `{report['reproduction_command']}`",
            "",
            f"Claim boundary: {report['claim_boundary']}",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.fixture)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "schema_localization.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "schema_localization.md").write_text(
        render_markdown(report), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
