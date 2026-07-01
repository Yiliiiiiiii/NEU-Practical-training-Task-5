"""Run SchemaPack local verification commands."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str], cwd: Path) -> None:
    print(f"\n== {name} ==")
    print(f"cwd={cwd}")
    print(" ".join(command))
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-evaluator", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--check-openapi", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    backend_python = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
    if backend_python.is_file():
        python = str(backend_python)
    npm = "npm.cmd" if sys.platform == "win32" else "npm"

    run_step("backend pytest", [python, "-m", "pytest", "-q"], ROOT / "backend")
    run_step("backend ruff", [python, "-m", "ruff", "check", "."], ROOT / "backend")
    if not args.skip_frontend:
        run_step("frontend build", [npm, "run", "build"], ROOT / "frontend")
    if args.check_openapi:
        run_step("openapi export", [python, "scripts/export_openapi.py"], ROOT)
    if args.include_evaluator:
        run_step(
            "production-like evaluator",
            [python, "scripts/eval_production_like.py"],
            ROOT,
        )


if __name__ == "__main__":
    main()
