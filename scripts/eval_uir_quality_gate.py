from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.uir import UIRDocument  # noqa: E402
from app.services.uir_quality_gate_service import UIRQualityGateService  # noqa: E402
from real_world_uir_common import DATASET_DIR, markdown_cell, read_json  # noqa: E402


def discover_uir_files(fixtures: Path) -> list[Path]:
    root = fixtures if fixtures.name == "uir" else fixtures / "uir"
    return sorted(root.rglob("*.json"))


def run_eval(fixtures: Path) -> dict[str, Any]:
    service = UIRQualityGateService()
    reports = []
    for path in discover_uir_files(fixtures):
        data = read_json(path)
        uir = UIRDocument.model_validate(data)
        report = service.evaluate(uir)
        reports.append(
            {
                "path": str(path.resolve().relative_to(ROOT)),
                **report.model_dump(mode="json"),
            }
        )

    status_counts = Counter(item["status"] for item in reports)
    issue_counts: Counter[str] = Counter()
    for report in reports:
        issue_counts.update(issue["code"] for issue in report["issues"])

    total = len(reports)
    average_quality_score = (
        round(sum(item["quality_score"] for item in reports) / total, 4)
        if total
        else 0.0
    )
    return {
        "summary": {
            "total": total,
            "pass": status_counts["pass"],
            "review": status_counts["review"],
            "reject": status_counts["reject"],
            "unsupported": status_counts["unsupported"],
            "average_quality_score": average_quality_score,
            "issue_counts": dict(sorted(issue_counts.items())),
            "allow_auto_accept_count": sum(
                1 for item in reports if item["mapping_policy"]["allow_auto_accept"]
            ),
        },
        "reports": reports,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    summary = data["summary"]
    lines = [
        "# UIR Quality Gate Evaluation",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key, value in summary.items():
        if key == "issue_counts":
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        lines.append(f"| {markdown_cell(key)} | {markdown_cell(value)} |")

    lines.extend(
        [
            "",
            "## Documents",
            "",
            "| doc_id | status | score | schema | route_confidence | issues |",
            "| --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    for report in data["reports"]:
        issue_codes = ", ".join(issue["code"] for issue in report["issues"]) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(report["doc_id"]),
                    markdown_cell(report["status"]),
                    markdown_cell(report["quality_score"]),
                    markdown_cell(report.get("supported_doc_type") or "-"),
                    markdown_cell(report["schema_route_confidence"]),
                    markdown_cell(issue_codes),
                ]
            )
            + " |"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=DATASET_DIR)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports" / "uir_quality_gate_eval_report.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=ROOT / "reports" / "uir_quality_gate_eval_report.md",
    )
    args = parser.parse_args()

    result = run_eval(args.fixtures)
    write_json(args.out, result)
    write_markdown(args.markdown, result)
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
