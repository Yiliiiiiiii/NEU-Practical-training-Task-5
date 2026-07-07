"""Aggregate strict-validation gaps from SchemaPack package reports."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase_c_report_metadata import attach_run_metadata  # noqa: E402


REPORT_NAMES = (
    "metadata.json",
    "mapping_report.json",
    "transform_report.json",
    "validation_report.json",
)
FAILURE_TYPE_BY_CODE = {
    "required_field_missing": "missing_required",
    "required_field_unmapped": "missing_required",
    "field_type_invalid": "wrong_type",
    "date_type_error": "wrong_type",
    "number_type_error": "wrong_type",
    "date_format_error": "date_format_invalid",
    "date_format_invalid": "date_format_invalid",
    "datetime_format_error": "date_format_invalid",
    "datetime_format_invalid": "date_format_invalid",
    "array_item_invalid": "array_item_invalid",
    "enum_value_invalid": "enum_invalid",
}


def report_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        issue
        for key in ("issues", "errors", "warnings")
        for issue in report.get(key, [])
        if isinstance(issue, dict)
    ]


def failure_type(issue: dict[str, Any]) -> str | None:
    explicit = issue.get("failure_type")
    if explicit:
        return str(explicit)
    code = issue.get("code")
    return FAILURE_TYPE_BY_CODE.get(str(code), str(code)) if code else None


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def package_paths(packages_root: Path) -> list[Path]:
    directories = sorted(
        path.parent
        for path in packages_root.rglob("validation_report.json")
        if path.is_file()
    )
    directory_set = {path.resolve() for path in directories}
    archives = sorted(
        path
        for path in packages_root.rglob("*.zip")
        if path.parent.resolve() not in directory_set
    )
    return [*archives, *directories]


def read_package_reports(package_path: Path) -> dict[str, dict[str, Any]]:
    if package_path.is_dir():
        return {
            name: read_json(package_path / name)
            for name in REPORT_NAMES
            if (package_path / name).is_file()
        }
    reports: dict[str, dict[str, Any]] = {}
    with ZipFile(package_path) as archive:
        available = set(archive.namelist())
        for name in REPORT_NAMES:
            if name not in available:
                continue
            payload = json.loads(archive.read(name).decode("utf-8"))
            if isinstance(payload, dict):
                reports[name] = payload
    return reports


def analyze(
    *,
    packages_root: str | Path,
    gold_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(packages_root)
    failures_by_doc_type: Counter[str] = Counter()
    required_missing_by_field: Counter[str] = Counter()
    review_required_by_field: Counter[str] = Counter()
    failure_categories: Counter[str] = Counter()
    items: list[dict[str, Any]] = []

    for package_path in package_paths(root):
        reports = read_package_reports(package_path)
        metadata = reports.get("metadata.json", {})
        mapping = reports.get("mapping_report.json", {})
        transform = reports.get("transform_report.json", {})
        validation = reports.get("validation_report.json", {})
        doc_id = str(metadata.get("doc_id") or package_path.stem)
        doc_type = str(
            metadata.get("schema_id")
            or validation.get("schema_id")
            or mapping.get("schema_id")
            or "unknown"
        )
        passed = bool(validation.get("passed"))

        required_missing = {
            str(issue.get("field_id"))
            for issue in validation.get("issues", [])
            if isinstance(issue, dict)
            and issue.get("code") == "required_field_missing"
            and issue.get("field_id")
        }
        required_missing.update(
            str(item.get("target_field_id"))
            for item in mapping.get("unmapped", [])
            if isinstance(item, dict)
            and item.get("required")
            and item.get("target_field_id")
        )
        review_items = [
            item
            for item in mapping.get("review_required_items", [])
            if isinstance(item, dict)
        ]

        if not passed:
            failures_by_doc_type[doc_type] += 1
        required_missing_by_field.update(required_missing)
        review_required_by_field.update(
            str(item["target_field_id"])
            for item in review_items
            if item.get("target_field_id")
        )
        for report in (validation, transform):
            failure_categories.update(
                category
                for issue in report_issues(report)
                if (category := failure_type(issue)) is not None
            )
        if review_items:
            failure_categories["semantic_review_required"] += len(review_items)

        items.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "package": str(package_path.relative_to(root)),
                "validation_passed": passed,
                "required_missing": sorted(required_missing),
                "review_required_count": len(review_items),
                "review_required_fields": sorted(
                    {
                        str(item["target_field_id"])
                        for item in review_items
                        if item.get("target_field_id")
                    }
                ),
                "failure_categories": sorted(
                    {
                        category
                        for report in (validation, transform)
                        for issue in report_issues(report)
                        if (category := failure_type(issue)) is not None
                    }
                    | ({"semantic_review_required"} if review_items else set())
                ),
                "schema_valid": bool(validation.get("schema_valid", passed)),
                "strict_semantic_valid": bool(
                    validation.get("strict_semantic_valid", passed)
                ),
            }
        )

    gold_rows = read_jsonl(Path(gold_path) if gold_path is not None else None)
    pass_count = sum(1 for item in items if item["validation_passed"])
    return {
        "summary": {
            "package_count": len(items),
            "validation_pass_count": pass_count,
            "validation_fail_count": len(items) - pass_count,
            "required_missing_count": sum(required_missing_by_field.values()),
            "review_required_count": sum(
                int(item["review_required_count"]) for item in items
            ),
        },
        "gold_case_count": len(gold_rows),
        "failures_by_doc_type": dict(sorted(failures_by_doc_type.items())),
        "required_missing_by_field": dict(sorted(required_missing_by_field.items())),
        "review_required_by_field": dict(sorted(review_required_by_field.items())),
        "failure_categories": dict(sorted(failure_categories.items())),
        "items": sorted(items, key=lambda item: item["doc_id"]),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Strict Validation Gap Analysis",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Packages | {summary['package_count']} |",
        f"| Validation passed | {summary['validation_pass_count']} |",
        f"| Validation failed | {summary['validation_fail_count']} |",
        f"| Required missing | {summary['required_missing_count']} |",
        f"| Review-required | {summary['review_required_count']} |",
        "",
        "## Failures by Document Type",
        "",
        "| Document type | Failures |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["failures_by_doc_type"].items()
    )
    lines.extend(
        [
            "",
            "## Required Missing by Field",
            "",
            "| Field | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["required_missing_by_field"].items()
    )
    lines.extend(
        [
            "",
            "## Review-required by Field",
            "",
            "| Field | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["review_required_by_field"].items()
    )
    lines.extend(
        [
            "",
            "## Failure Categories",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )
    lines.extend(
        f"| {name} | {count} |"
        for name, count in report["failure_categories"].items()
    )
    lines.extend(
        [
            "",
            "Package verification and strict semantic validation are reported separately.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(
    *,
    packages_root: str | Path,
    gold_path: str | Path | None,
    out_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    report = analyze(packages_root=packages_root, gold_path=gold_path)
    attach_run_metadata(report, packages_root=packages_root, gold_path=gold_path)
    write_json(Path(out_path), report)
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-root", required=True)
    parser.add_argument("--gold")
    parser.add_argument("--out", required=True)
    parser.add_argument("--markdown", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        packages_root=args.packages_root,
        gold_path=args.gold,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
