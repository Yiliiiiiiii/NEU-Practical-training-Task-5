"""Evaluate schema validation error localization for representative bad samples."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA = {
    "title": {"required": True, "type": str},
    "publish_date": {"required": True, "type": str, "pattern": r"^20\d{2}-\d{2}-\d{2}$"},
    "doc_type": {"required": True, "type": str, "enum": {"notice", "policy", "guide"}},
    "issuer": {"required": True, "type": str},
    "package": {"required": True, "type": dict},
}


def localize_errors(payload: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for field, rule in SCHEMA.items():
        if rule.get("required") and field not in payload:
            issues.append({"path": field, "code": "missing_required"})
            continue
        if field not in payload:
            continue
        value = payload[field]
        expected_type = rule.get("type")
        if isinstance(expected_type, type) and not isinstance(value, expected_type):
            issues.append({"path": field, "code": "wrong_type"})
            continue
        enum = rule.get("enum")
        if isinstance(enum, set) and value not in enum:
            issues.append({"path": field, "code": "wrong_enum"})
        pattern = rule.get("pattern")
        if isinstance(pattern, str) and isinstance(value, str) and not re.fullmatch(pattern, value):
            issues.append({"path": field, "code": "wrong_format"})
    package = payload.get("package")
    if isinstance(package, dict):
        manifest = package.get("manifest")
        if not isinstance(manifest, dict):
            issues.append({"path": "package.manifest", "code": "bad_nested_path"})
        elif manifest.get("checksum") in {None, ""}:
            issues.append({"path": "package.manifest.checksum", "code": "bad_nested_path"})
    return issues


def _cases() -> list[dict[str, Any]]:
    valid = {
        "title": "政策通知",
        "publish_date": "2025-01-16",
        "doc_type": "notice",
        "issuer": "国务院办公厅",
        "package": {"manifest": {"checksum": "abc"}},
    }
    return [
        {"case_id": "missing_required", "payload": {k: v for k, v in valid.items() if k != "issuer"}, "expected_path": "issuer"},
        {"case_id": "wrong_date_format", "payload": {**valid, "publish_date": "2025年1月16日"}, "expected_path": "publish_date"},
        {"case_id": "wrong_enum", "payload": {**valid, "doc_type": "unknown"}, "expected_path": "doc_type"},
        {"case_id": "wrong_type", "payload": {**valid, "title": 123}, "expected_path": "title"},
        {"case_id": "bad_nested_path", "payload": {**valid, "package": {"manifest": {}}}, "expected_path": "package.manifest.checksum"},
        {"case_id": "invalid_package_artifact", "payload": {**valid, "package": {}}, "expected_path": "package.manifest"},
    ]


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    issues = localize_errors(case["payload"])
    paths = [issue["path"] for issue in issues]
    passed = case["expected_path"] in paths
    return {**case, "localized_paths": paths, "issues": issues, "passed": passed}


def build_report() -> dict[str, Any]:
    results = [evaluate_case(case) for case in _cases()]
    total = len(results)
    localized = sum(1 for item in results if item["passed"])
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": total,
        "localized_count": localized,
        "localization_rate": localized / total if total else 0.0,
        "cases": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Schema Validation Localization",
        "",
        f"- Case count: {report['case_count']}",
        f"- Localization rate: {report['localization_rate']:.3f}",
        "",
        "| Case | Expected path | Localized paths | Passed |",
        "| --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['expected_path']} | "
            f"{', '.join(case['localized_paths'])} | {case['passed']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
