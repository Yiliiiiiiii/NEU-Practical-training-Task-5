import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.external_uir_adapter_service import ExternalUIRAdapterService  # noqa: E402
from app.services.schema_router_service import SchemaRouterService  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(
    *,
    input_path: str | Path,
    source_system: str,
    out_path: str | Path,
    report_path: str | Path,
    allow_llm: bool = False,
    route_schema: bool = False,
    route_report_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = read_json(Path(input_path))
    uir, adapter_report = ExternalUIRAdapterService().adapt_from_dict(
        payload,
        source_system=source_system,
        allow_llm=allow_llm,
    )
    write_json(Path(out_path), uir.model_dump(mode="json"))
    write_json(Path(report_path), adapter_report.model_dump(mode="json"))

    result: dict[str, Any] = {
        "doc_id": uir.doc_id,
        "adapter_report_status": adapter_report.status,
    }
    if route_schema:
        decision = SchemaRouterService().route(uir)
        route_payload = decision.model_dump(mode="json")
        if route_report_path is not None:
            write_json(Path(route_report_path), route_payload)
        result["schema_route"] = route_payload
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert external UIR JSON into SchemaPack UIRDocument JSON."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--source-system", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--allow-llm", action="store_true")
    parser.add_argument("--route-schema", action="store_true")
    parser.add_argument("--route-report")
    parser.add_argument(
        "--draft-if-unmatched",
        action="store_true",
        help="Reserved for the draft generator phase; no-op in this MVP.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(
        input_path=args.input,
        source_system=args.source_system,
        out_path=args.out,
        report_path=args.report,
        allow_llm=args.allow_llm,
        route_schema=args.route_schema,
        route_report_path=args.route_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
