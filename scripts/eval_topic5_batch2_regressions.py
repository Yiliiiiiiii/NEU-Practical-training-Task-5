"""Evaluate final Topic 5 status, package, and business-boundary regressions."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from topic5_reliability_common import BACKEND, ROOT, example_request

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.schemas.topic5_convert import Topic5ConvertRequest  # noqa: E402
from app.services.conversion_status_service import (  # noqa: E402
    ConversionStatusInput,
    ConversionStatusService,
)
from app.services.package_verifier_service import PackageVerifierService  # noqa: E402
from app.services.topic5_conversion_service import Topic5ConversionService  # noqa: E402

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_batch2_regressions" / "v1" / "report.json"
FORBIDDEN_BUSINESS_KEYS = {
    "task_id",
    "package_id",
    "execution_snapshot",
    "mapping_summary",
    "transform_summary",
    "metadata_template_report",
    "report_paths",
    "runtime_duration_ms",
    "api_key",
    "topic11_api_key",
    "mapping_report_path",
    "secret",
    "password",
    "access_token",
}


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _forbidden_paths(value: object, path: str = "$") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in FORBIDDEN_BUSINESS_KEYS:
                matches.append(child_path)
            matches.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return matches


def _status_cases() -> list[dict[str, Any]]:
    definitions = [
        ("completed", ConversionStatusInput(), "completed"),
        ("runtime_exception", ConversionStatusInput(runtime_exception=True), "failed"),
        ("package_write", ConversionStatusInput(package_write_failed=True), "failed"),
        (
            "package_verifier",
            ConversionStatusInput(package_verifier_passed=False),
            "failed",
        ),
        (
            "strict_metadata",
            ConversionStatusInput(metadata_passed=False, strict_metadata=True),
            "failed",
        ),
        (
            "strict_assertion",
            ConversionStatusInput(
                assertion_error_count=1, strict_output_assertions=True
            ),
            "failed",
        ),
        (
            "strict_provider",
            ConversionStatusInput(strict_provider_failed=True),
            "failed",
        ),
        (
            "mapping_review",
            ConversionStatusInput(mapping_review_item_count=1),
            "review_required",
        ),
        (
            "required_unmapped",
            ConversionStatusInput(unmapped_required_source_present_count=1),
            "review_required",
        ),
        (
            "inline_validation",
            ConversionStatusInput(schema_validation_passed=False),
            "review_required",
        ),
        (
            "registered_validation",
            ConversionStatusInput(schema_validation_passed=False),
            "review_required",
        ),
        (
            "non_strict_metadata",
            ConversionStatusInput(metadata_passed=False),
            "review_required",
        ),
        (
            "artifact_consistency",
            ConversionStatusInput(artifact_consistency_passed=False),
            "review_required",
        ),
        (
            "provider_fallback_review",
            ConversionStatusInput(
                provider_fallback_used=True,
                provider_fallback_requires_review=True,
            ),
            "review_required",
        ),
    ]
    return [
        {
            "case_id": case_id,
            "expected": expected,
            "actual": (actual := ConversionStatusService.determine(status_input)),
            "passed": actual == expected,
        }
        for case_id, status_input, expected in definitions
    ]


def _rehash_manifest_entry(package_dir: Path, filename: str) -> None:
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256((package_dir / filename).read_bytes()).hexdigest()
    for item in manifest["files"]:
        if item["path"] == filename:
            item["sha256"] = digest
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_evaluation() -> dict[str, Any]:
    status_cases = _status_cases()
    with TemporaryDirectory(prefix="topic5-final-regression-") as temp_dir:
        root = Path(temp_dir)
        payload = example_request()
        payload["uir"]["metadata"]["safe_nested"] = {
            "label": "business",
            "execution_snapshot": {"api_key": "must-not-leak"},
            "report_paths": {"mapping": "private.json"},
        }
        response = Topic5ConversionService(
            root, settings=Settings(storage_root=str(root), llm_mode="disabled")
        ).convert(Topic5ConvertRequest.model_validate(payload), create_package=True)
        package_dir = Path(str(response.package_zip_path)).parent
        content = json.loads((package_dir / "content.json").read_text(encoding="utf-8"))
        artifact = json.loads(
            (package_dir / "artifact_consistency_report.json").read_text(
                encoding="utf-8"
            )
        )
        base_verification = PackageVerifierService().verify_package(
            package_dir, strict=True
        )
        content["data"]["title"] = "tampered after verification"
        (package_dir / "content.json").write_text(
            json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _rehash_manifest_entry(package_dir, "content.json")
        tampered_verification = PackageVerifierService().verify_package(
            package_dir, strict=True
        )

    forbidden = _forbidden_paths(response.content_json)
    registered_case = next(
        case for case in status_cases if case["case_id"] == "registered_validation"
    )
    package_cases = [
        case
        for case in status_cases
        if case["case_id"] in {"package_write", "package_verifier"}
    ]
    passed = (
        all(case["passed"] for case in status_cases)
        and not forbidden
        and base_verification.passed
        and not tampered_verification.passed
        and artifact.get("nonempty_block_coverage") == 1.0
        and artifact.get("protected_block_integrity") == 1.0
    )
    return {
        "status": "passed" if passed else "failed",
        "dataset_id": "topic5_batch2_regressions",
        "dataset_version": "1.0.0",
        "commit_sha": _git_head(),
        "case_count": len(status_cases) + 3,
        "passed_count": sum(case["passed"] for case in status_cases)
        + int(not forbidden)
        + int(base_verification.passed)
        + int(not tampered_verification.passed),
        "status_truth_table_passed": all(case["passed"] for case in status_cases),
        "registered_validation_status_regression": int(not registered_case["passed"]),
        "package_failure_status_regression": sum(
            not case["passed"] for case in package_cases
        ),
        "content_json_internal_key_leak_count": len(forbidden),
        "content_json_internal_key_leak_paths": forbidden,
        "package_recomputed_consistency_rate": float(base_verification.passed),
        "package_tampering_detection_rate": float(not tampered_verification.passed),
        "nonempty_canonical_block_chunk_coverage": artifact.get(
            "nonempty_block_coverage"
        ),
        "protected_block_integrity": artifact.get("protected_block_integrity"),
        "status_cases": status_cases,
        "tampered_error_codes": sorted(
            {issue.code for issue in tampered_verification.errors}
        ),
        "reproduction_command": "python scripts/eval_topic5_batch2_regressions.py",
        "claim_boundary": "Declared Topic 5 runtime status and package contract regressions.",
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
