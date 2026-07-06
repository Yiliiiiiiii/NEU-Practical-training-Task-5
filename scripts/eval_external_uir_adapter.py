import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.candidate_service import CandidateService  # noqa: E402
from app.services.external_uir_adapter_service import ExternalUIRAdapterService  # noqa: E402
from app.services.mapping_service import MappingService  # noqa: E402
from app.services.schema_router_service import SchemaRouterService  # noqa: E402
from app.services.schema_service import SchemaService  # noqa: E402
from app.services.template_service import TemplateService  # noqa: E402


EXPECTED_ROUTE_FILES = {
    "sample_procurement_external.json": "sample_procurement_expected_route.json",
    "sample_policy_external.json": "sample_policy_expected_route.json",
    "sample_meeting_external.json": "sample_meeting_expected_route.json",
    "sample_general_external.json": "sample_general_expected_route.json",
}
PRODUCTION_LIKE = ROOT / "examples" / "production_like"
SECRET_MARKERS = ("sk-", "deepseek_api_key", "authorization", "bearer ")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fixture_contracts(fixtures_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(fixtures_dir / "expected" / "adapter_expected.jsonl")


def router_contracts(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(fixtures_dir / "expected" / "router_expected.jsonl")
    return {str(row["fixture"]): row for row in rows}


def badcase_contracts(fixtures_dir: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in read_jsonl(fixtures_dir / "expected" / "badcases.jsonl"):
        grouped.setdefault(str(row["fixture"]), []).append(row)
    return grouped


def fixture_paths(fixtures_dir: Path) -> list[Path]:
    return [
        fixtures_dir / str(row["fixture"])
        for row in fixture_contracts(fixtures_dir)
    ]


def expected_route(fixtures_dir: Path, fixture_path: Path) -> dict[str, Any]:
    relative = fixture_path.relative_to(fixtures_dir).as_posix()
    return router_contracts(fixtures_dir)[relative]


def count_secret_leaks(payload: Any) -> int:
    encoded = json.dumps(payload, ensure_ascii=False).lower()
    return sum(encoded.count(marker) for marker in SECRET_MARKERS)


def evaluate_badcases(
    *,
    fixture: str,
    uir: UIRDocument,
    contracts: list[dict[str, Any]],
) -> int:
    if not contracts:
        return 0
    schema_service = SchemaService(PRODUCTION_LIKE / "schemas")
    template_service = TemplateService(PRODUCTION_LIKE / "mapping_templates")
    violations = 0
    by_catalog: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for contract in contracts:
        key = (str(contract["schema_id"]), str(contract["template_id"]))
        by_catalog.setdefault(key, []).append(contract)
    for (schema_id, template_id), rows in by_catalog.items():
        report = MappingService().map_fields(
            f"eval_{uir.doc_id}",
            uir,
            schema_service.load_schema(schema_id),
            template_service.load_template(template_id),
            CandidateService().extract_candidates(f"eval_{uir.doc_id}", uir),
            options={
                "badcases": [
                    {
                        "source_field": row["source_label"],
                        "forbidden_target_fields": [row["forbidden_target"]],
                    }
                    for row in rows
                ]
            },
        )
        for row in rows:
            violations += sum(
                1
                for item in report.mappings
                if item["source_field_name"] == row["source_label"]
                and item["target_field_id"] == row["forbidden_target"]
                and item["status"] == "accepted"
            )
    return violations


def evaluate_fixture(
    fixtures_dir: Path,
    fixture_path: Path,
    *,
    adapter_expected: dict[str, Any] | None = None,
    router_expected: dict[str, Any] | None = None,
    badcases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    relative = fixture_path.relative_to(fixtures_dir).as_posix()
    adapter_expected = adapter_expected or next(
        row for row in fixture_contracts(fixtures_dir) if row["fixture"] == relative
    )
    router_expected = router_expected or expected_route(fixtures_dir, fixture_path)
    badcases = badcases or []
    payload = read_json(fixture_path)
    try:
        uir, adapter_report = ExternalUIRAdapterService().adapt_from_dict(
            payload,
            source_system="quality-polish",
        )
        UIRDocument.model_validate(uir.model_dump(mode="json"))
        decision = SchemaRouterService().route(uir, adapter_report=adapter_report)
        router_correct = (
            decision.selected_schema_id == router_expected["expected_schema_id"]
            and decision.selected_template_id
            == router_expected["expected_template_id"]
        )
        dumped = {
            "uir": uir.model_dump(mode="json"),
            "adapter_report": adapter_report.model_dump(mode="json"),
        }
        return {
            "fixture": relative,
            "doc_id": uir.doc_id,
            "adapter_id": adapter_report.adapter_id,
            "expected_adapter_id": adapter_expected["expected_adapter_id"],
            "adapter_selected_correctly": (
                adapter_report.adapter_id == adapter_expected["expected_adapter_id"]
            ),
            "adapter_passed": adapter_report.status in {"passed", "review_required"},
            "uir_validation_passed": True,
            "trace_coverage": adapter_report.trace_coverage,
            "selected_schema_id": decision.selected_schema_id,
            "selected_template_id": decision.selected_template_id,
            "expected_schema_id": router_expected["expected_schema_id"],
            "expected_template_id": router_expected["expected_template_id"],
            "router_top1_correct": router_correct,
            "router_review_required": decision.review_required,
            "router_confidence": decision.confidence,
            "badcase_violations": evaluate_badcases(
                fixture=relative,
                uir=uir,
                contracts=badcases,
            ),
            "llm_auto_accepted_count": adapter_report.llm_auto_accepted_count,
            "secret_leaks": count_secret_leaks(dumped),
            "warning_count": adapter_report.warning_count,
            "warnings": adapter_report.warnings,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - preserve all fixture failures in report.
        return {
            "fixture": relative,
            "adapter_selected_correctly": False,
            "adapter_passed": False,
            "uir_validation_passed": False,
            "trace_coverage": 0.0,
            "router_top1_correct": False,
            "router_review_required": True,
            "badcase_violations": 0,
            "llm_auto_accepted_count": 0,
            "secret_leaks": 0,
            "error": str(exc),
        }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    fixture_count = len(items)
    selection_correct = sum(
        1 for item in items if item["adapter_selected_correctly"]
    )
    router_correct = sum(1 for item in items if item["router_top1_correct"])
    trace_coverage = min(
        (float(item["trace_coverage"]) for item in items),
        default=0.0,
    )
    report = {
        "adapter_fixture_count": fixture_count,
        "adapter_selection_accuracy": round(
            selection_correct / fixture_count,
            4,
        )
        if fixture_count
        else 0.0,
        "uir_validation_pass_count": sum(
            1 for item in items if item["uir_validation_passed"]
        ),
        "trace_coverage": trace_coverage,
        "router_top1_accuracy": round(router_correct / fixture_count, 4)
        if fixture_count
        else 0.0,
        "router_review_required_count": sum(
            1 for item in items if item["router_review_required"]
        ),
        "badcase_violations": sum(
            int(item["badcase_violations"]) for item in items
        ),
        "llm_auto_accepted_count": sum(
            int(item["llm_auto_accepted_count"]) for item in items
        ),
        "secret_leaks": sum(int(item["secret_leaks"]) for item in items),
        "items": items,
    }
    report.update(
        {
            "dataset_size": fixture_count,
            "adapter_pass_count": sum(
                1 for item in items if item["adapter_passed"]
            ),
            "adapter_trace_coverage_count": sum(
                1 for item in items if float(item["trace_coverage"]) >= 0.95
            ),
            "schema_router_correct_count": router_correct,
            "schema_router_top1_accuracy": report["router_top1_accuracy"],
            "review_required_count": report["router_review_required_count"],
            "task_execute_pass_count": 0,
            "package_verify_pass_count": 0,
        }
    )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    keys = (
        "adapter_fixture_count",
        "adapter_selection_accuracy",
        "uir_validation_pass_count",
        "trace_coverage",
        "router_top1_accuracy",
        "router_review_required_count",
        "badcase_violations",
        "llm_auto_accepted_count",
        "secret_leaks",
    )
    lines = [
        "# External UIR Adapter Evaluation",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *[f"| {key} | {report[key]} |" for key in keys],
        "",
        "## Items",
        "",
        "| Fixture | Adapter | Router | Trace | Review | Warnings |",
        "|---|---|---|---:|---|---:|",
    ]
    for item in report["items"]:
        lines.append(
            f"| {item['fixture']} | "
            f"{'passed' if item['adapter_selected_correctly'] else 'failed'} | "
            f"{'passed' if item['router_top1_correct'] else 'failed'} | "
            f"{item['trace_coverage']} | "
            f"{item['router_review_required']} | "
            f"{item.get('warning_count', 0)} |"
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
    adapter_rows = fixture_contracts(base)
    router_rows = router_contracts(base)
    badcase_rows = badcase_contracts(base)
    items = [
        evaluate_fixture(
            base,
            base / str(row["fixture"]),
            adapter_expected=row,
            router_expected=router_rows[str(row["fixture"])],
            badcases=badcase_rows.get(str(row["fixture"]), []),
        )
        for row in adapter_rows
    ]
    report = summarize(items)
    write_json(Path(out_path), report)
    if markdown_path is not None:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate external UIR adapter fixtures.")
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
    failed = (
        report["adapter_selection_accuracy"] < 1.0
        or report["trace_coverage"] < 0.95
        or report["router_top1_accuracy"] < 0.85
        or report["badcase_violations"] > 0
        or report["llm_auto_accepted_count"] > 0
        or report["secret_leaks"] > 0
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
