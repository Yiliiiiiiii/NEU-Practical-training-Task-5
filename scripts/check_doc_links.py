"""Check local Markdown links in documentation files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        path = path if path.is_absolute() else ROOT / path
        if path.is_file() and path.suffix.lower() == ".md":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def _target_exists(source: Path, raw_target: str) -> bool:
    target = raw_target.strip().split("#", 1)[0]
    if not target or target.startswith(("http://", "https://", "mailto:", "app://")):
        return True
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if target.startswith("file:"):
        return True
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = source.parent / target_path
    return target_path.exists()


def check(paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for file in _markdown_files(paths):
        text = file.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(1)
                if not _target_exists(file, target):
                    rel = file.relative_to(ROOT)
                    failures.append(f"{rel}:{line_number}: missing link target {target}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failures = check(args.paths)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print("All local Markdown links exist.")


if __name__ == "__main__":
    main()
