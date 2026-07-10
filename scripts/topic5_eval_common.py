"""Shared report utilities for case-level Topic 5 evaluators."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_case_fixture(path: Path, *, dataset_id: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if payload.get("dataset_id") != dataset_id:
        raise ValueError(f"expected dataset_id {dataset_id}")
    if payload.get("version") != "2.0.0" or not isinstance(cases, list) or not cases:
        raise ValueError("Topic 5 evaluator fixture must be non-empty version 2.0.0")
    case_ids = [case.get("case_id") for case in cases]
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("Topic 5 evaluator case_id values must be non-empty and unique")
    return payload


def build_case_report(
    *,
    fixture_path: Path,
    fixture: dict[str, Any],
    cases: list[dict[str, Any]],
    metrics: dict[str, Any],
    reproduction_command: str,
    claim_boundary: str,
) -> dict[str, Any]:
    passed_count = sum(bool(case["passed"]) for case in cases)
    return {
        "dataset_id": fixture["dataset_id"],
        "dataset_version": fixture["version"],
        "dataset_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "commit_sha": current_commit_sha(),
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "passed_count": passed_count,
        **metrics,
        "failed_cases": [case for case in cases if not case["passed"]],
        "cases": cases,
        "reproduction_command": reproduction_command,
        "claim_boundary": claim_boundary,
    }


def current_commit_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
