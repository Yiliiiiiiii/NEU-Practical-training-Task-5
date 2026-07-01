"""Clean old runtime artifacts under a storage root."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

RUNTIME_DIR_NAMES = {"packages", "tasks", "reports"}
RUNTIME_SUFFIXES = {".json", ".jsonl", ".md", ".zip", ".txt", ".log"}


def cleanup_artifacts(
    storage_root: Path,
    *,
    days: int,
    dry_run: bool = True,
) -> dict[str, Any]:
    root = storage_root.resolve()
    if not root.exists():
        return {
            "storage_root": str(root),
            "dry_run": dry_run,
            "matched_count": 0,
            "deleted_count": 0,
            "files": [],
        }
    cutoff = datetime.now(UTC) - timedelta(days=days)
    matched: list[Path] = []
    deleted = 0
    for path in root.rglob("*"):
        resolved = path.resolve()
        if root != resolved and root not in resolved.parents:
            raise ValueError(f"path outside storage root: {resolved}")
        if not path.is_file() or not _is_runtime_artifact(root, path):
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if modified_at <= cutoff:
            matched.append(path)
            if not dry_run:
                path.unlink()
                deleted += 1
    if not dry_run:
        _remove_empty_dirs(root)
    return {
        "storage_root": str(root),
        "dry_run": dry_run,
        "matched_count": len(matched),
        "deleted_count": deleted,
        "files": [str(path) for path in matched],
    }


def _is_runtime_artifact(root: Path, path: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return bool(relative_parts) and (
        relative_parts[0] in RUNTIME_DIR_NAMES
        or path.suffix.lower() in RUNTIME_SUFFIXES
    )


def _remove_empty_dirs(root: Path) -> None:
    for path in sorted(
        (item for item in root.rglob("*") if item.is_dir()), reverse=True
    ):
        if root == path.resolve() or root not in path.resolve().parents:
            continue
        try:
            path.rmdir()
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, default=Path("storage"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = cleanup_artifacts(
        args.storage_root,
        days=args.days,
        dry_run=not args.delete,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"matched={result['matched_count']} deleted={result['deleted_count']} "
            f"dry_run={result['dry_run']}"
        )


if __name__ == "__main__":
    main()
