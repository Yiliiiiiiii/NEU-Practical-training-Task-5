"""Generate an inert, reviewable SchemaPack adapter plugin scaffold."""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "templates" / "adapter_plugin"
ADAPTER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def scaffold_adapter(
    adapter_id: str,
    output: str | Path,
    *,
    template_root: str | Path = TEMPLATE_ROOT,
) -> list[Path]:
    if not ADAPTER_ID_PATTERN.fullmatch(adapter_id):
        raise ValueError(
            "adapter_id must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores"
        )
    destination = Path(output)
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")
    replacements = {
        "{{ADAPTER_ID}}": adapter_id,
        "{{CLASS_NAME}}": _class_name(adapter_id),
    }
    template = Path(template_root)
    if destination.suffix == ".py":
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            _render(template / "adapter.py", replacements),
            encoding="utf-8",
        )
        return [destination]

    written: list[Path] = []
    for source in sorted(path for path in template.rglob("*") if path.is_file()):
        relative = source.relative_to(template)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render(source, replacements), encoding="utf-8")
        written.append(target)
    return written


def _render(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def _class_name(adapter_id: str) -> str:
    return "".join(part.capitalize() for part in adapter_id.split("_")) + "Adapter"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        files = scaffold_adapter(args.adapter_id, args.out)
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {"adapter_id": args.adapter_id, "files": [str(path) for path in files]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
