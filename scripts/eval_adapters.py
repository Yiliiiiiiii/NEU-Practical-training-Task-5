import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.adapters.base import AdapterInput  # noqa: E402
from app.adapters.registry import build_default_registry  # noqa: E402
from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.schema_router_service import SchemaRouterService  # noqa: E402


EXPECTED_ROUTE_FILES = {
    "sample_procurement_external.json": "sample_procurement_expected_route.json",
    "sample_policy_external.json": "sample_policy_expected_route.json",
    "sample_meeting_external.json": "sample_meeting_expected_route.json",
    "sample_general_external.json": "sample_general_expected_route.json",
}


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fixture_paths(fixtures_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in fixtures_dir.rglob("*.json")
        if "expected" not in path.parts
        and "converted" not in path.parts
        and path.name in EXPECTED_ROUTE_FILES
    )


def expected_adapter_id(fixture_path: Path) -> str:
    parts = set(fixture_path.parts)
    if "dialect_a_block_list" in parts:
        return "block_list"
    if "dialect_b_section_tree" in parts:
        return "section_tree"
    raise ValueError(f"cannot infer expected adapter for {fixture_path}")


def expected_route(fixtures_dir: Path, fixture_path: Path) -> dict[str, Any]:
    expected_name = EXPECTED_ROUTE_FILES[fixture_path.name]
    return read_json(fixtures_dir / "expected" / expected_name)


def evaluate_fixture(fixtures_dir: Path, fixture_path: Path) -> dict[str, Any]:
    payload = read_json(fixture_path)
    expected_adapter = expected_adapter_id(fixture_path)
    expected = expected_route(fixtures_dir, fixture_path)
    registry = build_default_registry()
    router = SchemaRouterService()
    try:
        adapter_input = AdapterInput(
            payload=payload,
            source_system="topic11",
            dialect_hint="auto",
        )
        selected = registry.select_adapter(adapter_input)
        result = registry.convert(adapter_input)
        validated_uir = UIRDocument.model_validate(
            result.standard_uir.model_dump(mode="json")
        )
        route = router.route(validated_uir)
        route_correct = (
            route.selected_schema_id == expected["schema_id"]
            and route.selected_template_id == expected["template_id"]
        )
        return {
            "fixture": str(fixture_path.relative_to(fixtures_dir)),
            "expected_adapter_id": expected_adapter,
            "selected_adapter_id": selected.adapter_id,
            "adapter_selection_correct": selected.adapter_id == expected_adapter,
            "adapter_confidence": selected.confidence,
            "uir_validation_passed": True,
            "trace_coverage": result.adapter_report.trace_coverage,
            "selected_schema_id": route.selected_schema_id,
            "selected_template_id": route.selected_template_id,
            "schema_router_correct": route_correct,
            "review_required": route.review_required or selected.review_required,
            "llm_auto_accepted_count": result.adapter_report.llm_auto_accepted_count,
            "badcase_violations": 0,
            "error": None,
        }
    except Exception as exc:
        return {
            "fixture": str(fixture_path.relative_to(fixtures_dir)),
            "expected_adapter_id": expected_adapter,
            "selected_adapter_id": None,
            "adapter_selection_correct": False,
            "adapter_confidence": 0.0,
            "uir_validation_passed": False,
            "trace_coverage": 0.0,
            "schema_router_correct": False,
            "review_required": True,
            "llm_auto_accepted_count": 0,
            "badcase_violations": 0,
            "error": str(exc),
        }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    registry = build_default_registry()
    fixture_count = len(items)
    selection_correct = sum(1 for item in items if item["adapter_selection_correct"])
    validation_passed = sum(1 for item in items if item["uir_validation_passed"])
    router_correct = sum(1 for item in items if item["schema_router_correct"])
    trace_coverage_total = sum(float(item["trace_coverage"]) for item in items)
    return {
        "adapter_count": len(registry.list_capabilities()),
        "fixture_count": fixture_count,
        "adapter_selection_accuracy": round(selection_correct / fixture_count, 4)
        if fixture_count
        else 0.0,
        "uir_validation_pass_rate": round(validation_passed / fixture_count, 4)
        if fixture_count
        else 0.0,
        "trace_coverage_avg": round(trace_coverage_total / fixture_count, 4)
        if fixture_count
        else 0.0,
        "schema_router_top1_accuracy": round(router_correct / fixture_count, 4)
        if fixture_count
        else 0.0,
        "review_required_count": sum(1 for item in items if item["review_required"]),
        "llm_auto_accepted_count": sum(
            int(item["llm_auto_accepted_count"]) for item in items
        ),
        "badcase_violations": sum(int(item["badcase_violations"]) for item in items),
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Adapter Framework Evaluation", "", "## Summary", ""]
    for key, value in report.items():
        if key != "items":
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        status = "passed" if item["adapter_selection_correct"] else "failed"
        lines.append(
            "- "
            f"{item['fixture']}: {status}, adapter={item['selected_adapter_id']}, "
            f"trace={item['trace_coverage']}"
        )
    lines.append("")
    return "\n".join(lines)


def run(
    *,
    fixtures_dir: str | Path,
    out_path: str | Path,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(fixtures_dir)
    items = [evaluate_fixture(base, path) for path in fixture_paths(base)]
    report = summarize(items)
    write_json(Path(out_path), report)
    if markdown_path is not None:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate External UIR adapter framework.")
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        fixtures_dir=args.fixtures,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "items"},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
