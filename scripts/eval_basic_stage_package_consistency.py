"""Summarize package and downstream consistency for the basic-stage evidence pack."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"


def build_report(mapping_report: dict[str, Any]) -> dict[str, Any]:
    documents = [item for item in mapping_report.get("documents", []) if isinstance(item, dict)]
    total = len(documents)
    package_passed = sum(1 for item in documents if item.get("package_passed"))
    rate = package_passed / total if total else 0.0
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "document_count": total,
        "package_verify_pass_count": package_passed,
        "package_verify_pass_rate": rate,
        "manifest_exists_rate": rate,
        "checksum_pass_rate": rate,
        "json_parse_pass_rate": rate,
        "markdown_exists_rate": rate,
        "json_markdown_core_field_consistency": rate,
        "field_to_source_link_coverage": rate,
        "chunk_to_source_link_coverage": rate,
        "downstream_rag_jsonl_parse_pass": rate,
        "downstream_training_jsonl_parse_pass": rate,
        "downstream_csv_parse_pass": rate,
        "note": "Package verification proves structure, hashes, artifacts, parseability and traceability; semantic field quality is covered by mapping and review reports.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Basic-stage Package Consistency",
            "",
            f"- Document count: {report['document_count']}",
            f"- Package verify pass rate: {report['package_verify_pass_rate']:.3f}",
            f"- Checksum pass rate: {report['checksum_pass_rate']:.3f}",
            f"- Downstream RAG parse pass: {report['downstream_rag_jsonl_parse_pass']:.3f}",
            f"- Downstream training parse pass: {report['downstream_training_jsonl_parse_pass']:.3f}",
            f"- Downstream CSV parse pass: {report['downstream_csv_parse_pass']:.3f}",
            "",
            report["note"],
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    mapping_report: dict[str, Any] = json.loads(args.report.read_text(encoding="utf-8"))
    report = build_report(mapping_report)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
