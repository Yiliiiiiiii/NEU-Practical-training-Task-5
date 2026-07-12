"""Run cross-platform Topic 5 Batch 2 verification with raw command evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DEFAULT_OUTPUT = ROOT / "reports" / "topic5_batch_2" / "verification"
TOPIC5_TASK_SCRIPTS = (
    "scripts/topic5_eval_common.py",
    "scripts/eval_topic5_metadata_contract.py",
    "scripts/eval_topic5_summary_faithfulness.py",
    "scripts/eval_topic5_artifact_consistency.py",
    "scripts/eval_topic5_entity_passthrough.py",
    "scripts/eval_topic5_topic11_adapter.py",
    "scripts/check_topic5_hard_gap_batch_1_gate.py",
    "scripts/check_topic5_batch_2_acceptance_gate.py",
    "scripts/check_topic5_batch_2_gate.py",
    "scripts/eval_downstream_contracts.py",
    "scripts/eval_topic5_batch2_regressions.py",
    "scripts/eval_topic5_concurrency.py",
    "scripts/eval_topic5_package_faults.py",
    "scripts/eval_topic5_performance.py",
    "scripts/eval_topic5_replay.py",
    "scripts/eval_topic5_runtime_equivalence.py",
    "scripts/eval_topic5_tag_quality_v2.py",
    "scripts/generate_topic5_batch_2_status.py",
    "scripts/run_topic5_batch_2_verification.py",
    "scripts/export_openapi.py",
)


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: tuple[str, ...]
    cwd: Path
    mandatory: bool = True


def npm_executable(current_platform: str | None = None) -> str:
    return "npm.cmd" if (current_platform or sys.platform) == "win32" else "npm"


def extended_evaluator_specs(output_dir: Path) -> list[CommandSpec]:
    evaluator_output = output_dir / "evaluator_reports"
    specs = [
        CommandSpec(
            "evaluator-tag-quality-v2",
            (
                sys.executable,
                "scripts/eval_topic5_tag_quality_v2.py",
                "--output",
                str(evaluator_output / "tag_quality_v2.json"),
            ),
            ROOT,
        ),
        CommandSpec(
            "evaluator-field-operations",
            (
                sys.executable,
                "scripts/eval_topic5_field_operations.py",
                "--out-dir",
                str(evaluator_output),
            ),
            ROOT,
        ),
        CommandSpec(
            "evaluator-schema-localization",
            (
                sys.executable,
                "scripts/eval_topic5_schema_localization.py",
                "--out-dir",
                str(evaluator_output),
            ),
            ROOT,
        ),
    ]
    specs.extend(
        CommandSpec(
            f"evaluator-mapping-v2-{split}",
            (
                sys.executable,
                "scripts/eval_topic5_mapping_v2.py",
                "--split",
                split,
                "--output",
                str(evaluator_output / f"mapping_v2_{split}.json"),
                "--fail-on-targets",
            ),
            ROOT,
        )
        for split in ("dev", "test")
    )
    specs.extend(
        [
            CommandSpec(
                "mapping-v2-gate",
                (
                    sys.executable,
                    "scripts/check_topic5_mapping_v2_gate.py",
                    "--output",
                    str(evaluator_output / "mapping_v2_gate.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-runtime-equivalence",
                (
                    sys.executable,
                    "scripts/eval_topic5_runtime_equivalence.py",
                    "--output",
                    str(evaluator_output / "runtime_equivalence.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-replay",
                (
                    sys.executable,
                    "scripts/eval_topic5_replay.py",
                    "--output",
                    str(evaluator_output / "replay.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-batch2-regressions",
                (
                    sys.executable,
                    "scripts/eval_topic5_batch2_regressions.py",
                    "--output",
                    str(evaluator_output / "batch2_regressions.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-package-faults",
                (
                    sys.executable,
                    "scripts/eval_topic5_package_faults.py",
                    "--output",
                    str(evaluator_output / "package_faults.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-concurrency",
                (
                    sys.executable,
                    "scripts/eval_topic5_concurrency.py",
                    "--output",
                    str(evaluator_output / "concurrency.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-performance",
                (
                    sys.executable,
                    "scripts/eval_topic5_performance.py",
                    "--baseline",
                    str(
                        ROOT
                        / "eval"
                        / "topic5_performance"
                        / "v1"
                        / "baseline.json"
                    ),
                    "--output",
                    str(evaluator_output / "performance.json"),
                ),
                ROOT,
            ),
            CommandSpec(
                "evaluator-downstream-contracts",
                (
                    sys.executable,
                    "scripts/eval_downstream_contracts.py",
                    "--output",
                    str(evaluator_output / "downstream_contracts.json"),
                ),
                ROOT,
            ),
        ]
    )
    return specs


def command_specs(output_dir: Path = DEFAULT_OUTPUT) -> list[CommandSpec]:
    npm = npm_executable()
    evaluator_output = output_dir / "evaluator_reports"
    return [
        CommandSpec(
            "backend-tests",
            (sys.executable, "-m", "pytest", "-q"),
            BACKEND,
        ),
        CommandSpec(
            "ruff",
            (sys.executable, "-m", "ruff", "check", "."),
            BACKEND,
        ),
        CommandSpec(
            "ruff-topic5-scripts",
            (sys.executable, "-m", "ruff", "check", *TOPIC5_TASK_SCRIPTS),
            ROOT,
        ),
        CommandSpec("frontend-tests", (npm, "run", "test"), FRONTEND),
        CommandSpec("frontend-build", (npm, "run", "build"), FRONTEND),
        CommandSpec(
            "openapi-drift",
            (sys.executable, "scripts/export_openapi.py", "--check"),
            ROOT,
        ),
        CommandSpec(
            "schemapack-contract-gate",
            (
                sys.executable,
                "scripts/check_schema_pack_contract_gate.py",
                "--fail-on-gate",
            ),
            ROOT,
        ),
        *[
            CommandSpec(
                f"evaluator-{name}",
                (
                    sys.executable,
                    f"scripts/eval_topic5_{name}.py",
                    "--output",
                    str(evaluator_output / f"{name}.json"),
                ),
                ROOT,
            )
            for name in (
                "metadata_contract",
                "summary_faithfulness",
                "artifact_consistency",
                "entity_passthrough",
                "topic11_adapter",
            )
        ],
        CommandSpec(
            "batch2-acceptance-gate",
            (
                sys.executable,
                "scripts/check_topic5_batch_2_acceptance_gate.py",
                "--report-dir",
                str(evaluator_output),
                "--output",
                str(output_dir / "acceptance_gate.json"),
            ),
            ROOT,
        ),
        *extended_evaluator_specs(output_dir),
    ]


def enforce_clean_tree(status_output: str, *, allow_dirty: bool) -> bool:
    dirty = bool(status_output.strip())
    if dirty and not allow_dirty:
        raise RuntimeError("git working tree is dirty; rerun with --allow-dirty to override")
    return dirty


def git_status(root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def git_commit_sha(root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def skipped_result(spec: CommandSpec, reason: str) -> dict[str, Any]:
    return {
        "name": spec.name,
        "command": list(spec.command),
        "cwd": str(spec.cwd),
        "stdout": "",
        "stderr": reason,
        "return_code": None,
        "duration_seconds": 0.0,
        "mandatory": spec.mandatory,
        "status": "skipped",
        "passed": False if spec.mandatory else True,
        "raw_log": None,
    }


def run_command(spec: CommandSpec, log_dir: Path) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            list(spec.command),
            cwd=spec.cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        result = skipped_result(spec, str(exc))
    else:
        result = {
            "name": spec.name,
            "command": list(spec.command),
            "cwd": str(spec.cwd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "return_code": completed.returncode,
            "duration_seconds": time.perf_counter() - started,
            "mandatory": spec.mandatory,
            "status": "passed" if completed.returncode == 0 else "failed",
            "passed": completed.returncode == 0,
            "raw_log": None,
        }
    result["duration_seconds"] = max(
        float(result["duration_seconds"]), time.perf_counter() - started
    )
    log_path = log_dir / f"{_safe_name(spec.name)}.log"
    log_path.write_text(_render_raw_log(result), encoding="utf-8")
    result["raw_log"] = str(log_path.resolve())
    return result


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "command"


def _render_raw_log(result: dict[str, Any]) -> str:
    command = subprocess.list2cmdline(result["command"])
    rendered = (
        f"command: {command}\n"
        f"cwd: {result['cwd']}\n"
        f"status: {result['status']}\n"
        f"return_code: {result['return_code']}\n"
        f"duration_seconds: {result['duration_seconds']:.6f}\n"
        "\n[stdout]\n"
        f"{result['stdout']}"
        "\n[stderr]\n"
        f"{result['stderr']}\n"
    )
    return rendered.rstrip() + "\n"


def tool_versions() -> dict[str, str]:
    npm = npm_executable()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git": _version(["git", "--version"]),
        "node": _version(["node", "--version"]),
        "npm": _version([npm, "--version"]),
    }


def _version(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return "unavailable"
    output = (completed.stdout or completed.stderr).strip()
    return output if completed.returncode == 0 and output else "unavailable"


def write_summary(
    output_dir: Path,
    *,
    commit_sha: str,
    dirty: bool,
    allow_dirty: bool,
    records: list[dict[str, Any]],
    tool_versions: dict[str, str],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    mandatory = [record for record in records if record["mandatory"]]
    github_actions = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
    github_sha = os.getenv("GITHUB_SHA") if github_actions else None
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": commit_sha,
        "dirty_tree": dirty,
        "allow_dirty": allow_dirty,
        "tool_versions": tool_versions,
        "commands": records,
        "passed": bool(mandatory) and all(record["passed"] for record in mandatory),
        "full_backend_tests_passed": _named_passed(records, "backend-tests"),
        "ruff_clean": _named_passed(records, "ruff")
        and _named_passed(records, "ruff-topic5-scripts"),
        "ruff_topic5_scripts_clean": _named_passed(
            records, "ruff-topic5-scripts"
        ),
        "frontend_tests_passed": _named_passed(records, "frontend-tests"),
        "frontend_build_passed": _named_passed(records, "frontend-build"),
        "openapi_export_passed": _named_passed(records, "openapi-drift"),
        "schema_pack_contract_gate_passed": _named_passed(
            records, "schemapack-contract-gate"
        ),
        "batch2_acceptance_gate_passed": _named_passed(
            records, "batch2-acceptance-gate"
        ),
        "github_ci_passed": github_actions
        and github_sha == commit_sha
        and bool(mandatory)
        and all(record["passed"] for record in mandatory),
        "github_ci_commit_sha": github_sha,
    }
    path = output_dir / "verification_summary.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _named_passed(records: list[dict[str, Any]], name: str) -> bool:
    return any(record["name"] == name and record["passed"] for record in records)


def read_final_gate_result(
    path: Path, command_record: dict[str, Any]
) -> dict[str, Any]:
    if not path.is_file():
        failure = "final_gate_output_missing"
    else:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failure = "final_gate_output_invalid"
        else:
            if isinstance(report, dict):
                return report
            failure = "final_gate_output_invalid"
    return {
        "passed": False,
        "status": "failed",
        "failed_conditions": [failure],
        "command_status": command_record.get("status"),
        "command_return_code": command_record.get("return_code"),
        "raw_log": command_record.get("raw_log"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    commit_sha = git_commit_sha()
    try:
        dirty = enforce_clean_tree(git_status(), allow_dirty=args.allow_dirty)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None

    records = [
        run_command(spec, args.output_dir / "raw_logs")
        for spec in command_specs(args.output_dir)
    ]
    summary_path = write_summary(
        args.output_dir,
        commit_sha=commit_sha,
        dirty=dirty,
        allow_dirty=args.allow_dirty,
        records=records,
        tool_versions=tool_versions(),
    )
    final_gate_command = [
        sys.executable,
        "scripts/check_topic5_batch_2_gate.py",
        "--report-dir",
        str(args.output_dir),
        "--verification",
        str(summary_path),
        "--output",
        str(args.output_dir / "final_gate.json"),
    ]
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        final_gate_command.append("--allow-pending-github-ci")
    final_gate_record = run_command(
        CommandSpec("batch2-final-gate", tuple(final_gate_command), ROOT),
        args.output_dir / "raw_logs",
    )
    records.append(final_gate_record)
    summary_path = write_summary(
        args.output_dir,
        commit_sha=commit_sha,
        dirty=dirty,
        allow_dirty=args.allow_dirty,
        records=records,
        tool_versions=tool_versions(),
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    final_gate = read_final_gate_result(
        args.output_dir / "final_gate.json", final_gate_record
    )
    payload["batch2_final_gate_passed"] = final_gate["passed"]
    payload["batch2_final_gate_status"] = final_gate["status"]
    payload["batch2_final_gate_failed_conditions"] = final_gate.get(
        "failed_conditions", []
    )
    if final_gate.get("failed_conditions") in (
        ["final_gate_output_missing"],
        ["final_gate_output_invalid"],
    ):
        payload["batch2_final_gate_error"] = {
            "command_status": final_gate.get("command_status"),
            "command_return_code": final_gate.get("command_return_code"),
            "raw_log": final_gate.get("raw_log"),
        }
    summary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote verification summary to {summary_path}")
    raise SystemExit(0 if payload["passed"] else 1)


if __name__ == "__main__":
    main()
