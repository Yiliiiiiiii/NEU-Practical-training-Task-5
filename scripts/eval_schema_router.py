import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.adapters.base import AdapterInput  # noqa: E402
from app.adapters.registry import build_default_registry  # noqa: E402
from app.services.schema_router_service import SchemaRouterService  # noqa: E402
from scripts.eval_adapters import (  # noqa: E402
    expected_route,
    fixture_paths,
    read_json,
    write_json,
)


def evaluate_fixture(fixtures_dir: Path, fixture_path: Path) -> dict[str, Any]:
    payload = read_json(fixture_path)
    expected = expected_route(fixtures_dir, fixture_path)
    try:
        adapter_result = build_default_registry().convert(
            AdapterInput(
                payload=payload,
                source_system="topic11",
                dialect_hint="auto",
            )
        )
        decision = SchemaRouterService().route(
            adapter_result.standard_uir,
            adapter_report=adapter_result.adapter_report,
        )
        candidate_ids = [candidate.schema_id for candidate in decision.candidates]
        expected_schema_id = str(expected["schema_id"])
        top1_correct = bool(candidate_ids and candidate_ids[0] == expected_schema_id)
        top2_correct = expected_schema_id in candidate_ids[:2]
        evidence_covered = bool(
            decision.candidates and decision.candidates[0].evidence
        )
        unsafe_auto_route = not top1_correct and not decision.review_required
        return {
            "fixture": str(fixture_path.relative_to(fixtures_dir)),
            "expected_schema_id": expected_schema_id,
            "selected_schema_id": decision.selected_schema_id,
            "candidate_schema_ids": candidate_ids,
            "confidence": decision.confidence,
            "top1_correct": top1_correct,
            "top2_correct": top2_correct,
            "review_required": decision.review_required,
            "unsafe_auto_route": unsafe_auto_route,
            "evidence_covered": evidence_covered,
            "route_version": decision.route_version,
            "error": None,
        }
    except Exception as exc:
        return {
            "fixture": str(fixture_path.relative_to(fixtures_dir)),
            "expected_schema_id": expected["schema_id"],
            "selected_schema_id": None,
            "candidate_schema_ids": [],
            "confidence": 0.0,
            "top1_correct": False,
            "top2_correct": False,
            "review_required": True,
            "unsafe_auto_route": False,
            "evidence_covered": False,
            "route_version": None,
            "error": str(exc),
        }


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    fixture_count = len(items)
    top1_count = sum(1 for item in items if item["top1_correct"])
    top2_count = sum(1 for item in items if item["top2_correct"])
    evidence_count = sum(1 for item in items if item["evidence_covered"])
    return {
        "route_version": SchemaRouterService.ROUTE_VERSION,
        "fixture_count": fixture_count,
        "top1_accuracy": round(top1_count / fixture_count, 4)
        if fixture_count
        else 0.0,
        "top2_accuracy": round(top2_count / fixture_count, 4)
        if fixture_count
        else 0.0,
        "review_required_count": sum(
            1 for item in items if item["review_required"]
        ),
        "unsafe_auto_route_count": sum(
            1 for item in items if item["unsafe_auto_route"]
        ),
        "route_evidence_coverage": round(evidence_count / fixture_count, 4)
        if fixture_count
        else 0.0,
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Schema Router v2 Evaluation", "", "## Summary", ""]
    for key, value in report.items():
        if key != "items":
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Items", ""])
    for item in report["items"]:
        status = "passed" if item["top1_correct"] else "failed"
        lines.append(
            f"- {item['fixture']}: {status}, selected={item['selected_schema_id']}, "
            f"confidence={item['confidence']}"
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
    parser = argparse.ArgumentParser(description="Evaluate Schema Router v2.")
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
