import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.uir import UIRDocument  # noqa: E402
from eval_external_uir_adapter import (  # noqa: E402
    count_secret_leaks,
    fixture_contracts,
    read_json,
    router_contracts,
    write_json,
)


def evaluate_fixture(
    *,
    base_url: str,
    fixtures_dir: Path,
    adapter_expected: dict[str, Any],
    router_expected: dict[str, Any],
) -> dict[str, Any]:
    fixture = str(adapter_expected["fixture"])
    payload = read_json(fixtures_dir / fixture)
    result: dict[str, Any] = {
        "fixture": fixture,
        "convert_passed": False,
        "import_passed": False,
        "uir_validation_passed": False,
        "adapter_selected_correctly": False,
        "trace_coverage": 0.0,
        "router_top1_correct": False,
        "router_review_required": True,
        "selected_schema_id": None,
        "selected_template_id": None,
        "expected_schema_id": router_expected["expected_schema_id"],
        "expected_template_id": router_expected["expected_template_id"],
        "llm_auto_accepted_count": 0,
        "badcase_violations": 0,
        "secret_leaks": 0,
        "error": None,
    }
    try:
        body = {
            "payload": payload,
            "source_system": "quality-polish",
            "dialect_hint": "auto",
            "route_schema": True,
            "allow_llm": False,
        }
        convert = post_json(base_url, "/api/v1/external-uir/convert", body)
        result["convert_passed"] = True
        standard_uir = convert.get("standard_uir", {})
        UIRDocument.model_validate(standard_uir)
        result["uir_validation_passed"] = True
        route = convert.get("route_report") or {}
        result["selected_schema_id"] = route.get("selected_schema_id")
        result["selected_template_id"] = route.get("selected_template_id")
        result["router_review_required"] = bool(route.get("review_required"))
        result["router_top1_correct"] = (
            result["selected_schema_id"] == router_expected["expected_schema_id"]
            and result["selected_template_id"]
            == router_expected["expected_template_id"]
        )
        adapter_report = convert.get("adapter_report") or {}
        result["adapter_selected_correctly"] = (
            adapter_report.get("adapter_id")
            == adapter_expected["expected_adapter_id"]
        )
        result["trace_coverage"] = float(
            adapter_report.get("trace_coverage") or 0.0
        )
        result["llm_auto_accepted_count"] = int(
            adapter_report.get("llm_auto_accepted_count") or 0
        )
        result["secret_leaks"] += count_secret_leaks(convert)

        imported = post_json(base_url, "/api/v1/external-uir/import", body)
        result["import_passed"] = bool(imported.get("doc_id"))
        result["secret_leaks"] += count_secret_leaks(imported)
    except Exception as exc:  # noqa: BLE001 - preserve all fixture failures in report.
        result["error"] = str(exc)
    return result


def post_json(base_url: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        base_url.rstrip("/") + path,
        json=body,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"{path} returned non-object JSON")
    return data


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    fixture_count = len(items)
    selection_correct = sum(
        1 for item in items if item["adapter_selected_correctly"]
    )
    router_correct = sum(1 for item in items if item["router_top1_correct"])
    return {
        "adapter_fixture_count": fixture_count,
        "adapter_selection_accuracy": round(
            selection_correct / fixture_count,
            4,
        )
        if fixture_count
        else 0.0,
        "convert_pass_count": sum(1 for item in items if item["convert_passed"]),
        "import_pass_count": sum(1 for item in items if item["import_passed"]),
        "uir_validation_pass_count": sum(
            1 for item in items if item["uir_validation_passed"]
        ),
        "trace_coverage": min(
            (float(item["trace_coverage"]) for item in items),
            default=0.0,
        ),
        "router_top1_accuracy": round(router_correct / fixture_count, 4)
        if fixture_count
        else 0.0,
        "router_review_required_count": sum(
            1 for item in items if item["router_review_required"]
        ),
        "llm_auto_accepted_count": sum(
            int(item["llm_auto_accepted_count"]) for item in items
        ),
        "badcase_violations": sum(
            int(item["badcase_violations"]) for item in items
        ),
        "secret_leaks": sum(int(item["secret_leaks"]) for item in items),
        "fixture_count": fixture_count,
        "secret_leak_count": sum(int(item["secret_leaks"]) for item in items),
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    keys = (
        "adapter_fixture_count",
        "adapter_selection_accuracy",
        "convert_pass_count",
        "import_pass_count",
        "uir_validation_pass_count",
        "trace_coverage",
        "router_top1_accuracy",
        "router_review_required_count",
        "badcase_violations",
        "llm_auto_accepted_count",
        "secret_leaks",
    )
    lines = [
        "# External UIR API Evaluation",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *[f"| {key} | {report[key]} |" for key in keys],
        "",
        "## Items",
        "",
    ]
    for item in report["items"]:
        passed = (
            item["convert_passed"]
            and item["import_passed"]
            and item["adapter_selected_correctly"]
            and item["router_top1_correct"]
            and float(item["trace_coverage"]) >= 0.95
        )
        lines.append(
            f"- {item['fixture']}: {'passed' if passed else 'failed'}, "
            f"selected={item.get('selected_schema_id')}, "
            f"expected={item.get('expected_schema_id')}"
        )
    lines.append("")
    return "\n".join(lines)


def run(
    *,
    base_url: str,
    fixtures_dir: str | Path,
    out_path: str | Path,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(fixtures_dir)
    router_rows = router_contracts(base)
    items = [
        evaluate_fixture(
            base_url=base_url,
            fixtures_dir=base,
            adapter_expected=row,
            router_expected=router_rows[str(row["fixture"])],
        )
        for row in fixture_contracts(base)
    ]
    report = summarize(items)
    write_json(Path(out_path), report)
    if markdown_path is not None:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate External UIR API fixtures.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        base_url=args.base_url,
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
        report["convert_pass_count"] != report["adapter_fixture_count"]
        or report["import_pass_count"] != report["adapter_fixture_count"]
        or report["adapter_selection_accuracy"] < 1.0
        or report["trace_coverage"] < 0.95
        or report["router_top1_accuracy"] < 0.85
        or report["badcase_violations"] > 0
        or report["llm_auto_accepted_count"] > 0
        or report["secret_leaks"] > 0
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
