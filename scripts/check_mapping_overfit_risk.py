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
REAL_WORLD_UIR_DIR = ROOT / "examples" / "real_world" / "uir"

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
SAMPLE_TEXT_SNIPPET_PATTERNS = [
    r"[\u4e00-\u9fff]{2,}(?:市|县|区).{0,12}第\s*\d+\s*届.{0,12}第\s*\d+\s*次.{0,8}会议",
    r"[\u4e00-\u9fff]{2,}(?:市|县|区).{0,12}第\d+届.{0,12}第\d+次.{0,8}会议",
]
SOURCE_PATH_SPECIFIC_PATTERNS = [
    r"examples[/\\]real_world[/\\]uir[/\\].*real_(?:policy|general|meeting|procurement)_",
]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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
                        "file": _display_path(path),
                        "line": line_number,
                        "pattern": pattern,
                        "excerpt": line.strip()[:240],
                    }
                )
    return findings


def _line_findings_for_snippets(
    path: Path,
    snippets: set[str],
) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for snippet in snippets:
            if snippet in line:
                findings.append(
                    {
                        "file": _display_path(path),
                        "line": line_number,
                        "pattern": "real_world_title_snippet",
                        "snippet": snippet,
                        "excerpt": line.strip()[:240],
                    }
                )
    return findings


def _real_title_snippets() -> set[str]:
    snippets: set[str] = set()
    if not REAL_WORLD_UIR_DIR.exists():
        return snippets
    for path in REAL_WORLD_UIR_DIR.rglob("real_*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        metadata = value.get("metadata", {})
        candidates: list[str] = []
        if isinstance(metadata, dict):
            for key in ("title", "source_title", "document_title"):
                item = metadata.get(key)
                if isinstance(item, str):
                    candidates.append(item)
        blocks = value.get("blocks", [])
        if isinstance(blocks, list):
            for block in blocks[:8]:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str) and block.get("type") == "heading":
                    candidates.append(text)
        for candidate in candidates:
            compact = re.sub(r"\s+", "", candidate)
            if len(compact) >= 8:
                snippets.add(compact[:16])
    return snippets


def build_report(paths: list[Path]) -> dict[str, Any]:
    files = _iter_files(paths)
    doc_id_findings: list[dict[str, Any]] = []
    gold_findings: list[dict[str, Any]] = []
    sample_text_findings: list[dict[str, Any]] = []
    source_path_findings: list[dict[str, Any]] = []
    title_snippet_findings: list[dict[str, Any]] = []
    title_snippets = _real_title_snippets()
    for path in files:
        doc_id_findings.extend(_matches(path, DOC_ID_PATTERNS))
        gold_findings.extend(_matches(path, GOLD_LEAKAGE_PATTERNS))
        sample_text_findings.extend(_matches(path, SAMPLE_TEXT_SNIPPET_PATTERNS))
        source_path_findings.extend(_matches(path, SOURCE_PATH_SPECIFIC_PATTERNS))
        title_snippet_findings.extend(_line_findings_for_snippets(path, title_snippets))
    risk_level = "low"
    if (
        gold_findings
        or doc_id_findings
        or sample_text_findings
        or source_path_findings
        or title_snippet_findings
    ):
        risk_level = "high"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scanned_files": len(files),
        "summary": {
            "risk_level": risk_level,
            "doc_id_specific_rules_found": len(doc_id_findings),
            "gold_leakage_found": len(gold_findings),
            "sample_text_snippet_findings": len(sample_text_findings),
            "source_path_specific_findings": len(source_path_findings),
            "real_title_snippet_findings": len(title_snippet_findings),
            "review_inflation_risk": "not_evaluated",
            "dev_test_gap": "not_evaluated",
            "decision": "Pass" if risk_level == "low" else "Fail",
        },
        "findings": {
            "doc_id_specific_rules": doc_id_findings,
            "gold_leakage": gold_findings,
            "sample_text_snippets": sample_text_findings,
            "source_path_specific": source_path_findings,
            "real_title_snippets": title_snippet_findings,
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
        f"- sample_text_snippet_findings: {summary['sample_text_snippet_findings']}",
        f"- source_path_specific_findings: {summary['source_path_specific_findings']}",
        f"- real_title_snippet_findings: {summary['real_title_snippet_findings']}",
        f"- review_inflation_risk: {summary['review_inflation_risk']}",
        f"- dev_test_gap: {summary['dev_test_gap']}",
        f"- decision: {summary['decision']}",
        "",
        "## Findings",
        "",
    ]
    for group in (
        "doc_id_specific_rules",
        "gold_leakage",
        "sample_text_snippets",
        "source_path_specific",
        "real_title_snippets",
    ):
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
