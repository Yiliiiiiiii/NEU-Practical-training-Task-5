"""Export the FastAPI OpenAPI schema for local docs and frontend reference."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app  # noqa: E402


def export_openapi(output_path: Path) -> dict[str, Any]:
    schema = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "openapi.json",
        help="Path to write the OpenAPI JSON schema.",
    )
    args = parser.parse_args()
    schema = export_openapi(args.output)
    print(f"exported {len(schema.get('paths', {}))} paths to {args.output}")


if __name__ == "__main__":
    main()
