import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
TOPIC5_TASK_SCRIPTS = {
    "scripts/topic5_eval_common.py",
    "scripts/eval_topic5_metadata_contract.py",
    "scripts/eval_topic5_summary_faithfulness.py",
    "scripts/eval_topic5_artifact_consistency.py",
    "scripts/eval_topic5_entity_passthrough.py",
    "scripts/eval_topic5_topic11_adapter.py",
    "scripts/check_topic5_hard_gap_batch_1_gate.py",
    "scripts/check_topic5_batch_2_acceptance_gate.py",
    "scripts/run_topic5_batch_2_verification.py",
    "scripts/export_openapi.py",
}


def _load_runner() -> ModuleType:
    path = ROOT / "scripts" / "run_topic5_batch_2_verification.py"
    spec = importlib.util.spec_from_file_location("topic5_batch2_ci_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ci_runs_batch_2_verification_on_windows_and_linux() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    runner = (ROOT / "scripts" / "run_topic5_batch_2_verification.py").read_text(
        encoding="utf-8"
    )

    for marker in (
        "matrix.os",
        "windows-latest",
        "ubuntu-latest",
        "actions/setup-python@v5",
        "actions/setup-node@v4",
        "python -m pip install -r backend/requirements.txt",
        "npm ci",
        "python scripts/run_topic5_batch_2_verification.py",
    ):
        assert marker in workflow

    for marker in (
        '"backend-tests"',
        '"ruff"',
        '"frontend-tests"',
        '"frontend-build"',
        '"openapi-drift"',
        '"schemapack-contract-gate"',
        '"batch2-acceptance-gate"',
    ):
        assert marker in runner

    assert "secrets." not in workflow


def test_ci_lints_topic5_task_scripts_explicitly_from_repo_root() -> None:
    runner = _load_runner()

    spec = next(
        spec for spec in runner.command_specs() if spec.name == "ruff-topic5-scripts"
    )

    assert spec.mandatory is True
    assert spec.cwd == ROOT
    assert spec.command[:4] == (sys.executable, "-m", "ruff", "check")
    assert TOPIC5_TASK_SCRIPTS <= set(spec.command[4:])
    assert not {".", "scripts", "scripts/"} & set(spec.command[4:])
