"""Scan mapping code and templates for overfitting risk signals."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "mapping_overfit_risk_report.json"
DEFAULT_MD = ROOT / "reports" / "mapping_overfit_risk_report.md"
DEFAULT_SCAN_PATHS = [
    ROOT / "backend" / "app",
    ROOT / "examples" / "production_like" / "mapping_templates",
    ROOT / "examples" / "production_like" / "schemas",
]

DOC_ID_PATTERNS = [
    r"real_policy_",
    r"real_general_",
    r"real_meeting_",
    r"real_procurement_",
    r"doc_id\s*==",
    r"source_path\s*==\s*[\"']examples/real_world/uir/",
]
GOLD_LEAKAGE_PATTERNS = [
    r"mapping_gold\.jsonl",
    r"mapping_gold_dev\.jsonl",
    r"mapping_gold_test\.jsonl",
    r"mapping_gold_blind\.jsonl",
    r"known_badcases",
    r"expected_mappings",
    r"expected_review_required",
]


def _iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            files.extend(
                child
                for child in path.rglob("*")
                if child.is_file() and child.suffix in {".py", ".json", ".yaml", ".yml"}
            )
    return sorted(files)


def _matches(path: Path, patterns: list[str]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[dict[str, Any]] = []
    for pattern in patterns:
        regex = re.compile(pattern)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                findings.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "line": line_number,
                        "pattern": pattern,
                        "excerpt": line.strip()[:240],
                    }
                )
    return findings


def build_report(paths: list[Path]) -> dict[str, Any]:
    files = _iter_files(paths)
    doc_id_findings: list[dict[str, Any]] = []
    gold_findings: list[dict[str, Any]] = []
    for path in files:
        doc_id_findings.extend(_matches(path, DOC_ID_PATTERNS))
        gold_findings.extend(_matches(path, GOLD_LEAKAGE_PATTERNS))
    risk_level = "low"
    if gold_findings or doc_id_findings:
        risk_level = "high"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scanned_files": len(files),
        "summary": {
            "risk_level": risk_level,
            "doc_id_specific_rules_found": len(doc_id_findings),
            "gold_leakage_found": len(gold_findings),
            "review_inflation_risk": "not_evaluated",
            "dev_test_gap": "not_evaluated",
            "decision": "Pass" if risk_level == "low" else "Fail",
        },
        "findings": {
            "doc_id_specific_rules": doc_id_findings,
            "gold_leakage": gold_findings,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Mapping Overfit Risk Report",
        "",
        "## Summary",
        "",
        f"- risk_level: {summary['risk_level']}",
        f"- doc_id_specific_rules_found: {summary['doc_id_specific_rules_found']}",
        f"- gold_leakage_found: {summary['gold_leakage_found']}",
        f"- review_inflation_risk: {summary['review_inflation_risk']}",
        f"- dev_test_gap: {summary['dev_test_gap']}",
        f"- decision: {summary['decision']}",
        "",
        "## Findings",
        "",
    ]
    for group in ("doc_id_specific_rules", "gold_leakage"):
        findings = report["findings"][group]
        lines.append(f"### {group}")
        if findings:
            for item in findings:
                lines.append(
                    f"- {item['file']}:{item['line']} `{item['pattern']}` "
                    f"{item['excerpt']}"
                )
        else:
            lines.append("- None")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--scan-path", type=Path, action="append")
    args = parser.parse_args()

    paths = args.scan_path or DEFAULT_SCAN_PATHS
    report = build_report(paths)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    if report["summary"]["decision"] != "Pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
