"""Build existing-schema-compatible UIR files from the local real-world cache."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from extract_docx_to_uir import extract_docx
from extract_html_to_uir import extract_html
from extract_pdf_to_uir import extract_pdf
from real_world_uir_common import (
    ExtractionResult,
    build_uir,
    dataset_paths,
    markdown_cell,
    read_json,
    sha256_bytes,
    write_json_atomic,
)

DOC_TYPE_DIRS = {
    "policy_doc": "policy",
    "procurement_doc": "procurement",
    "contract_doc": "contract",
    "meeting_doc": "meeting",
    "general_doc": "general",
}


def _extract(
    source_format: str,
    content: bytes,
    source_url: str,
) -> ExtractionResult:
    if source_format == "html":
        return extract_html(content, source_url=source_url)
    if source_format == "pdf":
        return extract_pdf(content)
    if source_format == "docx":
        return extract_docx(content)
    if source_format == "txt":
        text = content.decode("utf-8", errors="replace").strip()
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        if not paragraphs:
            return ExtractionResult(
                title="",
                blocks=[],
                status="rejected",
                reason="empty_extraction",
                extraction_method="utf8_text",
            )
        return ExtractionResult(
            title=paragraphs[0],
            blocks=[
                {
                    "type": "heading" if index == 0 else "paragraph",
                    "level": 1 if index == 0 else None,
                    "text": paragraph,
                }
                for index, paragraph in enumerate(paragraphs)
            ],
            extraction_method="utf8_text",
        )
    return ExtractionResult(
        title="",
        blocks=[],
        status="rejected",
        reason="unsupported_source_format",
    )


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    totals = report["totals"]
    collection_totals = report["collection_totals"]
    lines = [
        "# Real-world Extraction Report",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Sources | {totals['sources']} |",
        f"| Extracted | {totals['extracted']} |",
        f"| Rejected | {totals['rejected']} |",
        f"| Skipped | {totals['skipped']} |",
        f"| Downloaded | {collection_totals['downloaded']} |",
        f"| Collection failed | {collection_totals['failed']} |",
        "",
        "## Source formats",
        "",
        "| Format | Count |",
        "| --- | ---: |",
    ]
    for source_format, count in sorted(report["by_format"].items()):
        lines.append(f"| {markdown_cell(source_format)} | {count} |")
    lines.extend(
        [
            "",
            "| Source ID | Format | Status | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["items"]:
        lines.append(
            "| {source_id} | {source_format} | {status} | {reason} |".format(
                source_id=markdown_cell(item["source_id"]),
                source_format=markdown_cell(item["source_format"]),
                status=markdown_cell(item["status"]),
                reason=markdown_cell(item.get("reason", "")),
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_dataset(
    *,
    manifest_path: Path,
    cache_dir: Path,
    uir_dir: Path,
    reports_dir: Path,
    source_ids: set[str] | None = None,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest items must be a list")

    report_items: list[dict[str, Any]] = []
    selected_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id", ""))
        if source_ids and source_id not in source_ids:
            continue
        if item.get("status") not in {"fetched", "extracted"}:
            continue
        selected_count += 1
        report_item = {
            "source_id": source_id,
            "source_format": str(item.get("source_format", "")),
        }
        try:
            cached_path = cache_dir / str(item["cached_path"])
            content = cached_path.read_bytes()
            if sha256_bytes(content) != item.get("source_sha256"):
                raise ValueError("source_hash_mismatch")
            result = _extract(
                str(item["source_format"]),
                content,
                str(item["source_url"]),
            )
            if result.status != "extracted":
                item["status"] = result.status
                reason_key = (
                    "skip_reason" if result.status == "skipped" else "failure_reason"
                )
                item[reason_key] = result.reason
                report_item.update({"status": result.status, "reason": result.reason})
                rejected_path = uir_dir / "_rejected" / f"{source_id}.json"
                write_json_atomic(
                    rejected_path,
                    {
                        "source_id": source_id,
                        "status": result.status,
                        "reason": result.reason,
                    },
                )
                report_items.append(report_item)
                continue

            title = result.title or str(item.get("title", source_id))
            uir = build_uir(
                source=item,
                title=title,
                blocks=result.blocks,
                source_bytes=content,
                retrieved_at=str(item["retrieved_at"]),
                source_format=str(item["source_format"]),
                extraction_method=result.extraction_method,
                extracted_metadata=result.metadata,
            )
            directory = DOC_TYPE_DIRS[str(item["doc_type"])]
            output_path = uir_dir / directory / f"{source_id}.json"
            write_json_atomic(output_path, uir)
            item["status"] = "extracted"
            item["uir_path"] = output_path.relative_to(uir_dir.parent).as_posix()
            item.pop("failure_reason", None)
            item.pop("skip_reason", None)
            report_item.update(
                {
                    "status": "extracted",
                    "reason": "",
                    "uir_path": item["uir_path"],
                    "block_count": len(uir["blocks"]),
                }
            )
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            item["status"] = "rejected"
            item["failure_reason"] = reason
            report_item.update({"status": "rejected", "reason": reason})
        report_items.append(report_item)

    totals = {
        "sources": selected_count,
        "extracted": sum(item["status"] == "extracted" for item in report_items),
        "rejected": sum(item["status"] == "rejected" for item in report_items),
        "skipped": sum(item["status"] == "skipped" for item in report_items),
    }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": totals,
        "collection_totals": {
            "downloaded": sum(
                item.get("status") in {"fetched", "extracted"} for item in items
            ),
            "skipped": sum(item.get("status") == "skipped" for item in items),
            "failed": sum(
                item.get("status") in {"failed", "rejected"} for item in items
            ),
        },
        "by_format": dict(
            sorted(
                Counter(
                    str(item.get("source_format", "unknown"))
                    for item in items
                    if isinstance(item, dict)
                ).items()
            )
        ),
        "items": report_items,
    }
    write_json_atomic(manifest_path, manifest)
    write_json_atomic(reports_dir / "extraction_report.json", report)
    _write_markdown(reports_dir / "extraction_report.md", report)
    return report


def main() -> None:
    paths = dataset_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=paths["manifest"])
    parser.add_argument("--cache-dir", type=Path, default=paths["cache"])
    parser.add_argument("--uir-dir", type=Path, default=paths["uir"])
    parser.add_argument("--reports-dir", type=Path, default=paths["reports"])
    parser.add_argument("--source-id", action="append", dest="source_ids")
    args = parser.parse_args()
    report = build_dataset(
        manifest_path=args.manifest,
        cache_dir=args.cache_dir,
        uir_dir=args.uir_dir,
        reports_dir=args.reports_dir,
        source_ids=set(args.source_ids) if args.source_ids else None,
    )
    print(report["totals"])


if __name__ == "__main__":
    main()
