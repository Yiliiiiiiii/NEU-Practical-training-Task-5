from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_runner() -> ModuleType:
    path = ROOT / "scripts" / "run_topic5_batch_2_verification.py"
    assert path.is_file(), f"missing verification runner: {path}"
    spec = importlib.util.spec_from_file_location("topic5_batch2_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dirty_tree_requires_explicit_override() -> None:
    runner = _load_runner()

    with pytest.raises(RuntimeError, match="dirty"):
        runner.enforce_clean_tree(" M scripts/example.py\n", allow_dirty=False)

    assert runner.enforce_clean_tree(" M scripts/example.py\n", allow_dirty=True) is True
    assert runner.enforce_clean_tree("", allow_dirty=False) is False


def test_skipped_mandatory_command_is_not_passed() -> None:
    runner = _load_runner()
    spec = runner.CommandSpec(
        name="mandatory",
        command=(sys.executable, "-c", "pass"),
        cwd=ROOT,
        mandatory=True,
    )

    result = runner.skipped_result(spec, "tool unavailable")

    assert result["status"] == "skipped"
    assert result["passed"] is False
    assert result["return_code"] is None


def test_command_capture_writes_non_empty_raw_log(tmp_path: Path) -> None:
    runner = _load_runner()
    spec = runner.CommandSpec(
        name="capture",
        command=(
            sys.executable,
            "-c",
            "import sys; print('stdout-line'); print('stderr-line', file=sys.stderr)",
        ),
        cwd=ROOT,
        mandatory=True,
    )

    result = runner.run_command(spec, tmp_path)

    assert result["command"][0] == sys.executable
    assert result["cwd"] == str(ROOT)
    assert result["stdout"].strip() == "stdout-line"
    assert result["stderr"].strip() == "stderr-line"
    assert result["return_code"] == 0
    assert result["duration_seconds"] >= 0
    assert result["passed"] is True
    raw_log = Path(result["raw_log"])
    assert raw_log.is_file()
    assert raw_log.stat().st_size > 0


def test_summary_is_actual_json_and_fails_for_skipped_mandatory(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    spec = runner.CommandSpec(
        name="mandatory",
        command=(sys.executable, "-c", "pass"),
        cwd=ROOT,
        mandatory=True,
    )
    skipped = runner.skipped_result(spec, "tool unavailable")

    path = runner.write_summary(
        tmp_path,
        commit_sha="a" * 40,
        dirty=True,
        allow_dirty=True,
        records=[skipped],
        tool_versions={"python": sys.version.split()[0]},
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "verification_summary.json"
    assert path.stat().st_size > 0
    assert payload["commit_sha"] == "a" * 40
    assert payload["passed"] is False
    assert payload["commands"][0]["status"] == "skipped"


def test_cross_platform_command_selection_uses_current_python() -> None:
    runner = _load_runner()

    assert runner.npm_executable("win32") == "npm.cmd"
    assert runner.npm_executable("linux") == "npm"
    assert all(
        spec.command[0] in {sys.executable, "npm", "npm.cmd"}
        for spec in runner.command_specs()
    )


def test_schemapack_gate_is_configured_to_fail_on_gate() -> None:
    runner = _load_runner()

    spec = next(
        spec
        for spec in runner.command_specs()
        if spec.name == "schemapack-contract-gate"
    )

    assert "--fail-on-gate" in spec.command


def test_missing_final_gate_output_is_reported_without_crashing(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    record = {
        "status": "failed",
        "return_code": 1,
        "raw_log": str(tmp_path / "batch2-final-gate.log"),
    }

    result = runner.read_final_gate_result(tmp_path / "final_gate.json", record)

    assert result["passed"] is False
    assert result["status"] == "failed"
    assert result["failed_conditions"] == ["final_gate_output_missing"]
    assert result["command_return_code"] == 1
    assert result["raw_log"] == record["raw_log"]


def test_invalid_final_gate_output_is_reported_without_crashing(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    path = tmp_path / "final_gate.json"
    path.write_text("not-json", encoding="utf-8")

    result = runner.read_final_gate_result(
        path,
        {"status": "failed", "return_code": 2, "raw_log": "gate.log"},
    )

    assert result["passed"] is False
    assert result["failed_conditions"] == ["final_gate_output_invalid"]
    assert result["command_return_code"] == 2
