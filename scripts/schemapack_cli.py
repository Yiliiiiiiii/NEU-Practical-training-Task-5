"""Unified command-line client for the SchemaPack public API."""

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = ROOT / "sdk" / "python"
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from consumer_contract import (  # noqa: E402
    verify_batch,
    verify_consumer_contract,
    write_report,
)
from schemapack_client import SchemaPackClient  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.getenv("SCHEMAPACK_BASE_URL", "http://127.0.0.1:8000"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert-external")
    convert.add_argument("--input", required=True, type=Path)
    convert.add_argument("--out", required=True, type=Path)
    convert.add_argument("--source-system", default="external")
    convert.add_argument("--dialect")
    convert.add_argument("--route", action="store_true")

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--input", required=True, type=Path)
    import_parser.add_argument("--out", type=Path)

    create = subparsers.add_parser("create-task")
    create.add_argument("--doc-id", required=True)
    create.add_argument("--schema-id", required=True)
    create.add_argument("--template-id", required=True)
    create.add_argument("--schema-version", default="1.0.0")
    create.add_argument("--template-version", default="1.0.0")
    create.add_argument("--options", type=Path)
    create.add_argument("--out", type=Path)

    execute = subparsers.add_parser("execute-task")
    execute.add_argument("--task-id", required=True)
    execute.add_argument("--out", type=Path)

    download = subparsers.add_parser("download-package")
    download.add_argument("--task-id", required=True)
    download.add_argument("--out", required=True, type=Path)

    evaluate = subparsers.add_parser("eval")
    source = evaluate.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", type=Path)
    source.add_argument("--package-root", type=Path)
    evaluate.add_argument("--contract", required=True, type=Path)
    evaluate.add_argument("--out", required=True, type=Path)
    evaluate.add_argument("--markdown", type=Path)
    evaluate.add_argument("--min-pass-rate", type=float, default=0.95)

    list_schemas = subparsers.add_parser("list-schemas")
    list_schemas.add_argument("--out", type=Path)
    list_adapters = subparsers.add_parser("list-adapters")
    list_adapters.add_argument("--out", type=Path)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    client_factory: Callable[..., Any] = SchemaPackClient,
) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "eval":
        return _run_eval(args)

    api_key = os.getenv("SCHEMAPACK_API_KEY")
    with client_factory(args.base_url, api_key=api_key) as client:
        if args.command == "convert-external":
            result = client.convert_external_uir(
                _read_json(args.input),
                source_system=args.source_system,
                dialect_hint=args.dialect,
                route_schema=args.route,
            )
            standard_uir = result.get("standard_uir")
            if not isinstance(standard_uir, dict):
                raise ValueError("convert response is missing standard_uir")
            _write_json(standard_uir, args.out)
            _emit(result, None)
        elif args.command == "import":
            result = client.import_uir(_read_json(args.input))
            _emit(result, args.out)
        elif args.command == "create-task":
            result = client.create_task(
                args.doc_id,
                args.schema_id,
                args.template_id,
                schema_version=args.schema_version,
                template_version=args.template_version,
                options=_read_json(args.options) if args.options else {},
            )
            _emit(result, args.out)
        elif args.command == "execute-task":
            result = client.execute_task(args.task_id)
            _emit(result, args.out)
        elif args.command == "download-package":
            output = client.download_package(args.task_id, args.out)
            print(json.dumps({"output": str(output)}, ensure_ascii=False))
        elif args.command == "list-schemas":
            _emit(client.list_schemas(), args.out)
        elif args.command == "list-adapters":
            _emit(client.list_adapters(), args.out)
    return 0


def _run_eval(args: argparse.Namespace) -> int:
    if args.package:
        report = verify_consumer_contract(args.package, args.contract)
        passed = bool(report["passed"])
    else:
        report = verify_batch(args.package_root, args.contract)
        passed = report["consumer_contract_pass_rate"] >= args.min_pass_rate
    write_report(
        report,
        json_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _emit(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output is not None:
        _write_json(payload, output)
    print(text, end="")


def _write_json(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
