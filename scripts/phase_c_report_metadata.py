"""Phase C report provenance metadata helpers."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPORT_VERSION = "phase_c_v1"


def _git_value(args: list[str], default: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except Exception:
        return default
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else default


def build_run_metadata(
    *,
    packages_root: str | Path | None = None,
    gold_path: str | Path | None = None,
    badcases_path: str | Path | None = None,
    dataset_size: int | None = None,
    report_version: str = REPORT_VERSION,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    timestamp = generated_at.replace(":", "").replace("-", "").split(".")[0]
    return {
        "run_id": f"phase_c_{timestamp}",
        "generated_at": generated_at,
        "git_branch": _git_value(["branch", "--show-current"], "unknown"),
        "git_commit": _git_value(["rev-parse", "--short", "HEAD"], "unknown"),
        "packages_root": str(packages_root) if packages_root is not None else None,
        "gold_path": str(gold_path) if gold_path is not None else None,
        "badcases_path": str(badcases_path) if badcases_path is not None else None,
        "dataset_size": dataset_size,
        "report_version": report_version,
    }


def attach_run_metadata(
    report: dict[str, Any],
    *,
    packages_root: str | Path | None = None,
    gold_path: str | Path | None = None,
    badcases_path: str | Path | None = None,
    dataset_size: int | None = None,
) -> dict[str, Any]:
    if dataset_size is None:
        summary = report.get("summary", {})
        if isinstance(summary, dict):
            value = summary.get("dataset_size", summary.get("package_count"))
            dataset_size = value if isinstance(value, int) else None
    report["run_metadata"] = build_run_metadata(
        packages_root=packages_root,
        gold_path=gold_path,
        badcases_path=badcases_path,
        dataset_size=dataset_size,
    )
    return report
