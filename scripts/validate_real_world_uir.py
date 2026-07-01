"""Validate traceability, privacy, and current-schema compatibility of real-world UIR."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError
from real_world_uir_common import (
    VALID_DOC_TYPES,
    dataset_paths,
    markdown_cell,
    write_json_atomic,
)

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.uir import UIRDocument  # noqa: E402

REQUIRED_METADATA = {
    "title",
    "doc_type",
    "source_url",
    "source_site",
    "retrieved_at",
    "source_format",
    "source_sha256",
    "extraction_method",
    "extraction_version",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MOJIBAKE_MARKERS = ("Ã", "Â", "æ–", "å†", "å®", "�")
SENSITIVE_PATTERNS = {
    "mobile_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "identity_card": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "personal_email": re.compile(
        r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        r"(?![A-Za-z0-9.-])"
    ),
    "bank_card": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
}
NON_CONTENT_KEYS = {
    "block_id",
    "doc_id",
    "extraction_method",
    "path",
    "retrieved_at",
    "source_name",
    "source_sha256",
    "source_url",
    "uir_version",
}


def _finding(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _textual_values(value: Any, key: str | None = None) -> list[str]:
    if key in NON_CONTENT_KEYS:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            text
            for child_key, child_value in value.items()
            for text in _textual_values(child_value, str(child_key))
        ]
    if isinstance(value, list):
        return [text for child in value for text in _textual_values(child)]
    return []


def scan_sensitive_information(value: Any) -> list[dict[str, str]]:
    rendered = "\n".join(_textual_values(value))
    findings: list[dict[str, str]] = []
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(rendered):
            findings.append(
                _finding(
                    "possible_personal_sensitive_information",
                    "$",
                    f"matched {label}",
                )
            )
    return findings


def validate_uir_data(data: Any) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [_finding("invalid_json_shape", "$", "UIR must be a JSON object")]
    try:
        UIRDocument.model_validate(data)
    except ValidationError as exc:
        for error in exc.errors(include_url=False):
            path = ".".join(str(part) for part in error["loc"])
            findings.append(
                _finding("uir_schema_validation_failed", path, str(error["msg"]))
            )

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        findings.append(
            _finding("missing_metadata", "metadata", "metadata is required")
        )
        metadata = {}
    for key in sorted(REQUIRED_METADATA):
        if not metadata.get(key):
            findings.append(
                _finding(
                    "missing_required_metadata", f"metadata.{key}", f"{key} is required"
                )
            )

    doc_type = metadata.get("doc_type")
    if doc_type and doc_type not in VALID_DOC_TYPES:
        findings.append(
            _finding(
                "invalid_doc_type", "metadata.doc_type", f"unsupported {doc_type!r}"
            )
        )
    source_url = metadata.get("source_url")
    if source_url:
        parsed = urlsplit(str(source_url))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            findings.append(
                _finding(
                    "invalid_source_url", "metadata.source_url", "expected HTTP(S) URL"
                )
            )
    source_sha256 = metadata.get("source_sha256")
    if source_sha256 and not SHA256_PATTERN.fullmatch(str(source_sha256)):
        findings.append(
            _finding(
                "invalid_source_sha256",
                "metadata.source_sha256",
                "expected 64 lowercase hexadecimal characters",
            )
        )

    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        findings.append(_finding("invalid_blocks", "blocks", "blocks must be a list"))
        blocks = []
    if len(blocks) < 3:
        findings.append(
            _finding(
                "insufficient_blocks", "blocks", "at least three blocks are required"
            )
        )
    block_ids: set[str] = set()
    for index, block in enumerate(blocks):
        path = f"blocks.{index}"
        if not isinstance(block, dict):
            findings.append(_finding("invalid_block", path, "block must be an object"))
            continue
        block_id = str(block.get("block_id", ""))
        if block_id in block_ids:
            findings.append(
                _finding("duplicate_block_id", f"{path}.block_id", block_id)
            )
        block_ids.add(block_id)
        if (
            block.get("type") in {"heading", "paragraph"}
            and not str(block.get("text") or "").strip()
        ):
            findings.append(_finding("empty_block", f"{path}.text", "text is empty"))
        if block.get("type") == "table":
            rows = block.get("attributes", {}).get("rows")
            if not isinstance(rows, list) or not all(
                isinstance(row, dict) and "field" in row and "value" in row
                for row in rows
            ):
                findings.append(
                    _finding(
                        "invalid_table_rows", f"{path}.attributes.rows", "invalid rows"
                    )
                )

    rendered = json.dumps(data, ensure_ascii=False)
    if any(marker in rendered for marker in MOJIBAKE_MARKERS):
        findings.append(_finding("possible_mojibake", "$", "suspicious decoded text"))
    findings.extend(scan_sensitive_information(data))

    hints = metadata.get("hints")
    if isinstance(hints, dict):
        candidates = hints.get("candidate_fields", [])
        if isinstance(candidates, list):
            for index, candidate in enumerate(candidates):
                if not isinstance(candidate, dict):
                    continue
                path = f"metadata.hints.candidate_fields.{index}"
                if not candidate.get("evidence_text") and not candidate.get(
                    "evidence_block_ids"
                ):
                    findings.append(
                        _finding(
                            "missing_candidate_evidence", path, "evidence is required"
                        )
                    )
                confidence = candidate.get("confidence")
                if (
                    isinstance(confidence, int | float)
                    and confidence < 0.8
                    and not candidate.get("review_required")
                ):
                    findings.append(
                        _finding(
                            "low_confidence_without_review",
                            path,
                            "low-confidence candidate must require review",
                        )
                    )
    return findings


def _safe_rejected_path(source: Path, uir_dir: Path) -> Path:
    source_resolved = source.resolve()
    root_resolved = uir_dir.resolve()
    if root_resolved not in source_resolved.parents:
        raise ValueError("unsafe source path")
    rejected_dir = (uir_dir / "_rejected").resolve()
    if rejected_dir != root_resolved and root_resolved not in rejected_dir.parents:
        raise ValueError("unsafe rejected path")
    rejected_dir.mkdir(parents=True, exist_ok=True)
    return rejected_dir / source.name


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    totals = report["totals"]
    lines = [
        "# Real-world UIR Validation Report",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Total | {totals['total']} |",
        f"| Passed | {totals['passed']} |",
        f"| Failed | {totals['failed']} |",
        f"| Sensitive findings | {totals['sensitive']} |",
        f"| Mojibake findings | {totals['mojibake']} |",
        f"| Missing-field findings | {totals['missing_fields']} |",
        f"| Empty or mojibake findings | {totals['empty_or_mojibake']} |",
        "",
        "| File | Status | Findings |",
        "| --- | --- | --- |",
    ]
    for item in report["items"]:
        messages = "; ".join(finding["code"] for finding in item["findings"])
        lines.append(
            f"| {markdown_cell(item['path'])} | {item['status']} | "
            f"{markdown_cell(messages)} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_dataset(
    *,
    uir_dir: Path,
    reports_dir: Path,
    move_rejected: bool = True,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for path in sorted(uir_dir.glob("*/*.json")):
        if path.parent.name == "_rejected":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            findings = validate_uir_data(data)
            if isinstance(data, dict) and data.get("doc_id") != path.stem:
                findings.append(
                    _finding("doc_id_filename_mismatch", "doc_id", path.stem)
                )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            findings = [_finding("invalid_json", "$", str(exc))]
        status = "passed" if not findings else "failed"
        results.append(
            {
                "path": path.relative_to(uir_dir).as_posix(),
                "status": status,
                "findings": findings,
            }
        )
        if findings and move_rejected:
            destination = _safe_rejected_path(path, uir_dir)
            if destination.exists():
                destination.unlink()
            shutil.move(str(path), str(destination))

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {
            "total": len(results),
            "passed": sum(item["status"] == "passed" for item in results),
            "failed": sum(item["status"] == "failed" for item in results),
            "sensitive": sum(
                finding["code"] == "possible_personal_sensitive_information"
                for item in results
                for finding in item["findings"]
            ),
            "mojibake": sum(
                finding["code"] == "possible_mojibake"
                for item in results
                for finding in item["findings"]
            ),
            "missing_fields": sum(
                finding["code"]
                in {
                    "missing_metadata",
                    "missing_required_metadata",
                    "uir_schema_validation_failed",
                }
                for item in results
                for finding in item["findings"]
            ),
            "empty_or_mojibake": sum(
                finding["code"]
                in {
                    "empty_block",
                    "insufficient_blocks",
                    "invalid_blocks",
                    "possible_mojibake",
                }
                for item in results
                for finding in item["findings"]
            ),
        },
        "items": results,
    }
    write_json_atomic(reports_dir / "validation_report.json", report)
    _write_markdown(reports_dir / "validation_report.md", report)
    return report


def main() -> None:
    paths = dataset_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uir-dir", type=Path, default=paths["uir"])
    parser.add_argument("--reports-dir", type=Path, default=paths["reports"])
    parser.add_argument("--no-move-rejected", action="store_true")
    args = parser.parse_args()
    report = validate_dataset(
        uir_dir=args.uir_dir,
        reports_dir=args.reports_dir,
        move_rejected=not args.no_move_rejected,
    )
    print(report["totals"])
    raise SystemExit(0 if report["totals"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
