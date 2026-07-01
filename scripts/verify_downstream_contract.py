"""Verify SchemaPack packages from a downstream consumer's perspective."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from export_rag_corpus import export_rag_corpus  # noqa: E402
from export_structured_csv import export_structured_csv  # noqa: E402
from package_consumption import (  # noqa: E402
    PackageReadError,
    load_manifest,
    load_metadata,
    resolved_package_dir,
    validate_manifest_files,
)

REQUIRED_ARTIFACTS = {
    "manifest.json",
    "metadata.json",
    "content.json",
    "content.md",
    "chunks.jsonl",
    "canonical.json",
    "mapping_report.json",
    "validation_report.json",
    "content_organization_report.json",
    "verifier_report.json",
}


def verify_package(package_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    csv_passed = False
    rag_passed = False
    try:
        with resolved_package_dir(package_path) as package_dir:
            missing = sorted(
                name
                for name in REQUIRED_ARTIFACTS
                if not (package_dir / name).is_file()
            )
            if missing:
                raise PackageReadError(
                    "required artifacts missing: " + ", ".join(missing)
                )
            manifest = load_manifest(package_dir)
            validate_manifest_files(package_dir, manifest)
            metadata = load_metadata(package_dir)
            for key in ("schema_id", "template_id", "task_id", "doc_id"):
                if not metadata.get(key):
                    errors.append(f"metadata missing {key}")
            markdown = (package_dir / "content.md").read_text(encoding="utf-8").strip()
            if not markdown:
                errors.append("content.md is empty")
        with tempfile.TemporaryDirectory(prefix="downstream-contract-") as raw:
            temp = Path(raw)
            export_structured_csv(package_path, temp / "content.csv")
            csv_passed = True
            rag = export_rag_corpus(package_path, temp / "rag.jsonl")
            rag_passed = rag["row_count"] > 0
            if rag["missing_source_link_count"]:
                warnings.append(
                    f"{rag['missing_source_link_count']} chunks have no source links"
                )
    except (OSError, ValueError, PackageReadError) as exc:
        errors.append(str(exc))
    return {
        "package": str(package_path),
        "passed": not errors and csv_passed and rag_passed,
        "errors": errors,
        "warnings": warnings,
        "export_structured_csv_passed": csv_passed,
        "export_rag_corpus_passed": rag_passed,
    }


def run_batch(packages_root: Path) -> dict[str, Any]:
    packages: list[Path] = sorted(packages_root.rglob("*.zip"))
    if not packages:
        packages.extend(
            path.parent
            for path in sorted(packages_root.rglob("manifest.json"))
            if path.parent != packages_root
        )
    results = [verify_package(path) for path in packages]
    passed = sum(item["passed"] for item in results)
    return {
        "summary": {
            "package_count": len(results),
            "passed_count": passed,
            "failed_count": len(results) - passed,
        },
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Downstream Contract Evaluation Report",
        "",
        f"- Packages: {summary['package_count']}",
        f"- Passed: {summary['passed_count']}",
        f"- Failed: {summary['failed_count']}",
        "",
        "| Package | Passed | Errors | Warnings |",
        "| --- | --- | --- | --- |",
    ]
    for item in report["results"]:
        lines.append(
            f"| {item['package']} | {item['passed']} | {'; '.join(item['errors'])} | "
            f"{'; '.join(item['warnings'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path)
    group.add_argument("--packages-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    if args.package:
        result = verify_package(args.package)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(0 if result["passed"] else 1)
    report = run_batch(args.packages_root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if report["summary"]["failed_count"] == 0 else 1)


if __name__ == "__main__":
    main()
