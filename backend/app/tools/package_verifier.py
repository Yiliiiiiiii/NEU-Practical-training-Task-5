import argparse
import json
from pathlib import Path

from app.verifiers.package_verifier import verify_package_zip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a SchemaPack package ZIP.")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--max-json-bytes", type=int, default=5_000_000)
    args = parser.parse_args(argv)

    report = verify_package_zip(args.zip_path, max_json_bytes=args.max_json_bytes)
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
