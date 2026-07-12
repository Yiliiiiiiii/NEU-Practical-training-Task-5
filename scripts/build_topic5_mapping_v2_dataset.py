"""Materialize the reviewed, independently authored mapping-v2 source freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "eval" / "topic5_mapping_v2_source"
DEFAULT_OUTPUT = ROOT / "eval" / "topic5_mapping_v2"
BASELINE_ENGINE_COMMIT = "70ff30236d90a3c9de0534a8f6313e5bb559cbf5"


def _hashes(root: Path, paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _combined(files: dict[str, str]) -> str:
    return hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in files.items()).encode()
    ).hexdigest()


def write_hashes(output: Path) -> None:
    frozen = [
        path
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "hashes.json" and "reports" not in path.parts
    ]
    files = _hashes(output, frozen)
    report_paths = [
        path for path in sorted((output / "reports").glob("*.json")) if path.is_file()
    ]
    report_files = _hashes(output, report_paths)
    source_paths = [path for path in sorted(SOURCE.rglob("*")) if path.is_file()]
    source_files = _hashes(SOURCE, source_paths)
    groups: dict[str, str] = {}
    for group in ("uir", "target_schemas", "mapping_rules", "gold", "splits"):
        rows = [
            f"{name}:{digest}"
            for name, digest in files.items()
            if name.startswith(group + "/")
        ]
        groups[group] = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    dataset_sha = _combined(files)
    payload = {
        "dataset_id": "topic5_mapping_v2",
        "version": "2.0.0",
        "baseline_engine_commit": BASELINE_ENGINE_COMMIT,
        "dataset_sha256": dataset_sha,
        "groups": groups,
        "files": files,
        "source_path": SOURCE.relative_to(ROOT).as_posix(),
        "source_contract_sha256": _combined(source_files),
        "report_files": report_files,
    }
    hashes_path = output / "hashes.json"
    hashes_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output.parent / f"{output.name}.hashes.sha256").write_text(
        hashlib.sha256(hashes_path.read_bytes()).hexdigest() + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build(output: Path, *, force: bool = False) -> None:
    seal_path = output.parent / f"{output.name}.hashes.sha256"
    if (output.exists() or seal_path.exists()) and not force:
        raise FileExistsError(
            f"output already exists; pass --force to overwrite: {output}"
        )
    if output.exists():
        shutil.rmtree(output)
    if seal_path.exists():
        seal_path.unlink()
    shutil.copytree(SOURCE, output)
    write_hashes(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        build(args.output.resolve(), force=args.force)
    except Exception as exc:
        import sys

        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
