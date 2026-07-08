"""Evaluate production shadow mapping, or report why blind eval is blocked."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from check_production_shadow_gold_coverage import BLOCKER_REASON, build_report as coverage_report

ROOT = Path(__file__).resolve().parents[1]


def build_blocked_eval_report(
    *,
    manifest: Path,
    split: str,
    gold: Path,
    badcases: Path | None,
) -> dict[str, Any]:
    coverage = coverage_report(manifest, gold)
    if coverage["status"] != "passed":
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "status": "blocked",
            "split": split,
            "manifest": str(manifest),
            "gold": str(gold),
            "badcases": str(badcases) if badcases else None,
            "can_claim_0_85": False,
            "reason": BLOCKER_REASON,
            "coverage": coverage,
            "summary": {
                "blind_average_recall": 0.0,
                "auto_accepted_precision": 0.0,
                "mapped_or_review_recall": 0.0,
                "required_missing_rate": 1.0,
                "review_required_rate": 0.0,
                "badcase_violations": 0,
                "llm_auto_accepted_count": 0,
                "package_verification_rate": 0.0,
                "secret_leaks": 0,
                "report_consistency_passed": False,
            },
        }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "not_run",
        "split": split,
        "manifest": str(manifest),
        "gold": str(gold),
        "badcases": str(badcases) if badcases else None,
        "can_claim_0_85": False,
        "reason": "Production shadow corpus exists, but live blind mapping eval was not run.",
        "coverage": coverage,
        "summary": {},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase G Blind Set Evaluation",
        "",
        f"- Status: {report['status']}",
        f"- Split: {report['split']}",
        f"- Can claim 0.85: {report['can_claim_0_85']}",
        f"- Reason: {report['reason']}",
    ]
    if report.get("summary"):
        lines.extend(["", "## Summary", ""])
        for key, value in report["summary"].items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], out: Path, markdown: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", default="blind")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--badcases", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_blocked_eval_report(
        manifest=args.manifest,
        split=args.split,
        gold=args.gold,
        badcases=args.badcases,
    )
    write_reports(report, args.out, args.markdown)
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "not_run" else 2


if __name__ == "__main__":
    raise SystemExit(main())
