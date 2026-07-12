"""Inject package build faults and verify atomic cleanup and preservation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from topic5_reliability_common import BACKEND, ROOT, example_request

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_settings  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.manifest_service import ManifestService  # noqa: E402
from app.services.package_service import PackageBuildError, PackageService  # noqa: E402
from app.services.package_verifier_service import PackageVerifierService  # noqa: E402

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_package_faults" / "v1" / "report.json"


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


@contextmanager
def _client(storage_root: Path):
    settings = Settings(storage_root=str(storage_root), llm_mode="disabled")
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client


def _clean(storage_root: Path) -> tuple[bool, bool]:
    packages = storage_root / "packages"
    final_clean = not packages.exists() or not list(packages.glob("pkg_*"))
    temp_root = packages / ".tmp"
    temp_clean = not temp_root.exists() or not list(temp_root.iterdir())
    return final_clean, temp_clean


def _fault_case(name: str, expected_stage: str) -> dict[str, Any]:
    with TemporaryDirectory(prefix=f"topic5-fault-{name}-") as temp_dir:
        root = Path(temp_dir)

        def fail(*_args: Any, **_kwargs: Any) -> None:
            raise OSError(f"injected {name} fault")

        original_atomic = PackageService._atomic_write_text

        def fail_manifest(path: Path, value: str) -> None:
            if Path(path).name == "manifest.json":
                raise OSError("injected manifest fault")
            original_atomic(path, value)

        if name == "content":
            target, attribute, replacement = PackageService, "_write_semantic_files", fail
        elif name == "manifest":
            target, attribute, replacement = (
                PackageService,
                "_atomic_write_text",
                staticmethod(fail_manifest),
            )
        elif name == "verifier":
            target, attribute, replacement = PackageVerifierService, "verify_package", fail
        elif name == "zip":
            target, attribute, replacement = PackageService, "_write_deterministic_zip", fail
        elif name == "final_rename":
            target, attribute, replacement = PackageService, "_finalize_directory", fail
        else:
            raise ValueError(f"unknown fault case: {name}")

        actual_stage = None
        with patch.object(target, attribute, replacement):
            try:
                with _client(root) as client:
                    client.post(
                        "/api/v1/topic5/convert/package", json=example_request()
                    )
            except PackageBuildError as exc:
                actual_stage = exc.stage
        final_clean, temp_clean = _clean(root)
        passed = actual_stage == expected_stage and final_clean and temp_clean
        return {
            "case_id": name,
            "expected_stage": expected_stage,
            "actual_stage": actual_stage,
            "partial_final_package_count": 0 if final_clean else 1,
            "temporary_entry_count": 0 if temp_clean else 1,
            "passed": passed,
        }


def _prior_package_case() -> dict[str, Any]:
    with TemporaryDirectory(prefix="topic5-fault-prior-") as temp_dir:
        root = Path(temp_dir)
        with patch(
            "app.services.topic5_conversion_service.new_id",
            lambda _prefix: "preserved-task",
        ):
            with _client(root) as client:
                first = client.post(
                    "/api/v1/topic5/convert/package", json=example_request()
                ).json()
                zip_path = Path(first["package_zip_path"])
                before = ManifestService.sha256_file(zip_path)
                actual_stage = None
                try:
                    client.post(
                        "/api/v1/topic5/convert/package", json=example_request()
                    )
                except PackageBuildError as exc:
                    actual_stage = exc.stage
                after = ManifestService.sha256_file(zip_path)
        _final_clean, temp_clean = _clean(root)
        passed = (
            actual_stage == "final_rename"
            and zip_path.is_file()
            and before == after
            and temp_clean
        )
        return {
            "case_id": "prior_package_preservation",
            "expected_stage": "final_rename",
            "actual_stage": actual_stage,
            "prior_package_hash_before": before,
            "prior_package_hash_after": after,
            "temporary_entry_count": 0 if temp_clean else 1,
            "passed": passed,
        }


def run_evaluation() -> dict[str, Any]:
    cases = [
        _fault_case("content", "content_write"),
        _fault_case("manifest", "manifest_write"),
        _fault_case("verifier", "package_verify"),
        _fault_case("zip", "zip_create"),
        _fault_case("final_rename", "final_rename"),
        _prior_package_case(),
    ]
    partial_count = sum(case.get("partial_final_package_count", 0) for case in cases)
    temp_count = sum(case["temporary_entry_count"] for case in cases)
    passed_count = sum(case["passed"] for case in cases)
    passed = passed_count == len(cases) and partial_count == 0 and temp_count == 0
    return {
        "status": "passed" if passed else "failed",
        "dataset_id": "topic5_package_faults",
        "dataset_version": "1.0.0",
        "commit_sha": _git_head(),
        "case_count": len(cases),
        "passed_count": passed_count,
        "partial_package_survival_count": partial_count,
        "temporary_cleanup_failure_count": temp_count,
        "prior_package_preservation_rate": float(cases[-1]["passed"]),
        "cases": cases,
        "reproduction_command": "python scripts/eval_topic5_package_faults.py",
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
