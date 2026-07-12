"""Exercise concurrent Topic 5 package conversions through the HTTP API."""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

from topic5_reliability_common import BACKEND, ROOT, canonical_json_bytes, example_request

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.api.deps import get_settings  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.package_verifier_service import PackageVerifierService  # noqa: E402

DEFAULT_OUTPUT = ROOT / "eval" / "topic5_concurrency" / "v1" / "report.json"
TERMINAL_STATUSES = {"completed", "review_required", "failed"}


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _payload(group: str) -> dict[str, Any]:
    payload = copy.deepcopy(example_request())
    payload.pop("output_assertions", None)
    payload["uir"]["doc_id"] = f"concurrency-{group.lower()}"
    payload["uir"]["metadata"]["source"] = f"concurrency-{group}"
    payload["uir"]["metadata"]["group_marker"] = group
    payload["uir"]["metadata"]["document_title"] = f"Concurrent fixture {group}"
    payload["uir"]["blocks"][0]["text"] = f"Concurrent fixture {group}"
    payload["uir"]["blocks"][-1]["text"] = f"Isolated body for group {group}."
    return payload


async def _run_requests(storage_root: Path, request_count: int) -> list[dict[str, Any]]:
    settings = Settings(storage_root=str(storage_root), llm_mode="disabled")
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    payloads = [_payload("A" if index % 2 == 0 else "B") for index in range(request_count)]
    originals = copy.deepcopy(payloads)
    async with httpx.AsyncClient(transport=transport, base_url="http://topic5.test") as client:
        responses = await asyncio.gather(
            *[
                client.post("/api/v1/topic5/convert/package", json=payload)
                for payload in payloads
            ]
        )
    records = []
    for index, (response, payload, original) in enumerate(
        zip(responses, payloads, originals, strict=True)
    ):
        body = response.json()
        group = "A" if index % 2 == 0 else "B"
        package_path = Path(str(body.get("package_zip_path") or ""))
        package_dir = package_path.parent
        verifier = (
            PackageVerifierService().verify_package(package_dir, strict=True)
            if package_path.is_file()
            else None
        )
        content = (
            json.loads((package_dir / "content.json").read_text(encoding="utf-8"))
            if (package_dir / "content.json").is_file()
            else {}
        )
        records.append(
            {
                "index": index,
                "group": group,
                "http_status": response.status_code,
                "status": body.get("status"),
                "task_id": body.get("task_id"),
                "package_id": (body.get("package_metadata") or {}).get("package_id"),
                "semantic_artifact_hashes": body.get("semantic_artifact_hashes"),
                "package_valid": bool(verifier and verifier.passed),
                "group_marker": content.get("source_metadata", {}).get("group_marker"),
                "request_not_mutated": canonical_json_bytes(payload)
                == canonical_json_bytes(original),
            }
        )
    return records


def run_evaluation(request_count: int = 10) -> dict[str, Any]:
    if request_count < 10:
        raise ValueError("request_count must be at least 10")
    with TemporaryDirectory(prefix="topic5-concurrency-") as temp_dir:
        cases = asyncio.run(_run_requests(Path(temp_dir), request_count))
    task_ids = [case["task_id"] for case in cases]
    package_ids = [case["package_id"] for case in cases]
    hashes_by_group = {
        group: {
            json.dumps(case["semantic_artifact_hashes"], sort_keys=True)
            for case in cases
            if case["group"] == group
        }
        for group in ("A", "B")
    }
    checks = {
        "minimum_concurrency": len(cases) >= 10,
        "all_http_success": all(case["http_status"] == 200 for case in cases),
        "all_terminal": all(case["status"] in TERMINAL_STATUSES for case in cases),
        "unique_task_ids": len(set(task_ids)) == len(task_ids),
        "unique_package_ids": len(set(package_ids)) == len(package_ids),
        "identical_semantics_for_identical_inputs": all(
            len(values) == 1 for values in hashes_by_group.values()
        ),
        "distinct_semantics_for_distinct_inputs": hashes_by_group["A"]
        != hashes_by_group["B"],
        "no_cross_task_contamination": all(
            case["group_marker"] == case["group"] for case in cases
        ),
        "all_packages_valid": all(case["package_valid"] for case in cases),
        "no_shared_mutable_configuration": all(
            case["request_not_mutated"] for case in cases
        ),
    }
    passed = all(checks.values())
    return {
        "status": "passed" if passed else "failed",
        "dataset_id": "topic5_http_concurrency",
        "dataset_version": "1.0.0",
        "commit_sha": _git_head(),
        "request_count": len(cases),
        "terminal_status_rate": sum(
            case["status"] in TERMINAL_STATUSES for case in cases
        )
        / len(cases),
        "valid_package_rate": sum(case["package_valid"] for case in cases)
        / len(cases),
        "checks": checks,
        "failed_conditions": [name for name, value in checks.items() if not value],
        "cases": cases,
        "reproduction_command": "python scripts/eval_topic5_concurrency.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_evaluation(args.requests)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
