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


def _serialized_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_openapi(output_path: Path) -> dict[str, Any]:
    schema = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_serialized_schema(schema), encoding="utf-8")
    return schema


def check_openapi_drift(expected_path: Path) -> bool:
    if not expected_path.is_file():
        return False
    actual = _serialized_schema(create_app().openapi())
    return expected_path.read_text(encoding="utf-8") == actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "openapi.json",
        help="Path to write the OpenAPI JSON schema.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero when the committed OpenAPI JSON differs; do not rewrite it.",
    )
    args = parser.parse_args()
    if args.check:
        if not check_openapi_drift(args.output):
            print(f"OpenAPI drift detected for {args.output}")
            raise SystemExit(1)
        print(f"OpenAPI schema is current: {args.output}")
        return
    schema = export_openapi(args.output)
    print(f"exported {len(schema.get('paths', {}))} paths to {args.output}")


if __name__ == "__main__":
    main()
