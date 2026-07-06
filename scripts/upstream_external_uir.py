"""Convert a local raw document into adapter-compatible External UIR."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SUPPORTED_PROVIDERS = {"docling", "unstructured"}
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".html", ".htm"}
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
ProviderRunner = Callable[[Path], Any]


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        text = _normalize_text(" ".join(paragraph_lines))
        if text:
            blocks.append({"type": "paragraph", "text": text, "attributes": {}})
        paragraph_lines.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            blocks.append(
                {
                    "type": "heading",
                    "level": len(heading.group(1)),
                    "text": _normalize_text(heading.group(2)),
                    "attributes": {},
                }
            )
        elif not line:
            flush_paragraph()
        else:
            paragraph_lines.append(line)
    flush_paragraph()
    return blocks


def _run_docling(path: Path) -> dict[str, Any]:
    from docling.document_converter import DocumentConverter

    document = DocumentConverter().convert(path).document
    markdown = document.export_to_markdown()
    blocks = _markdown_blocks(markdown)
    return {
        "title": next(
            (
                block["text"]
                for block in blocks
                if block["type"] == "heading" and block.get("text")
            ),
            path.stem,
        ),
        "blocks": blocks,
        "metadata": {},
        "method": "docling",
    }


def _element_metadata(element: Any) -> dict[str, Any]:
    metadata = getattr(element, "metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        rendered = metadata.to_dict()
        return rendered if isinstance(rendered, dict) else {}
    return {}


def _run_unstructured(path: Path) -> dict[str, Any]:
    from unstructured.partition.auto import partition

    elements = partition(filename=str(path), strategy="fast")
    blocks: list[dict[str, Any]] = []
    for element in elements:
        text = _normalize_text(element)
        if not text:
            continue
        category = str(getattr(element, "category", "")).lower()
        metadata = _element_metadata(element)
        block_type = "paragraph"
        if category in {"title", "header"}:
            block_type = "heading"
        elif category == "table":
            block_type = "table"
        block: dict[str, Any] = {
            "type": block_type,
            "text": text,
            "attributes": {
                "unstructured_category": category or "unknown",
            },
        }
        page_number = metadata.get("page_number")
        if isinstance(page_number, int):
            block["source_anchor"] = {"page": page_number, "bbox": None}
        blocks.append(block)
    return {
        "title": next(
            (
                block["text"]
                for block in blocks
                if block["type"] == "heading" and block.get("text")
            ),
            path.stem,
        ),
        "blocks": blocks,
        "metadata": {},
        "method": "unstructured_fast",
    }


def _fallback_extract(path: Path, source_bytes: bytes) -> Any:
    if path.suffix.lower() == ".pdf":
        from extract_pdf_to_uir import extract_pdf

        return extract_pdf(source_bytes)
    if path.suffix.lower() == ".docx":
        from extract_docx_to_uir import extract_docx

        return extract_docx(source_bytes)

    from extract_html_to_uir import extract_html

    return extract_html(source_bytes, source_url=path.resolve().as_uri())


def _coerce_extraction(result: Any, *, default_method: str) -> dict[str, Any]:
    if isinstance(result, dict):
        status = str(result.get("status", "extracted"))
        reason = result.get("reason")
        title = _normalize_text(result.get("title"))
        blocks = result.get("blocks", [])
        metadata = result.get("metadata", {})
        method = str(
            result.get("method")
            or result.get("extraction_method")
            or default_method
        )
    else:
        status = str(getattr(result, "status", "extracted"))
        reason = getattr(result, "reason", None)
        title = _normalize_text(getattr(result, "title", ""))
        blocks = getattr(result, "blocks", [])
        metadata = getattr(result, "metadata", {})
        method = str(getattr(result, "extraction_method", "") or default_method)
    if status in {"rejected", "skipped", "failed"}:
        raise ValueError(str(reason or status))
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("empty_extraction")
    return {
        "title": title,
        "blocks": [block for block in blocks if isinstance(block, dict)],
        "metadata": metadata if isinstance(metadata, dict) else {},
        "method": method,
    }


def _external_chunks(
    blocks: list[dict[str, Any]],
    *,
    provider_used: str,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for index, block in enumerate(blocks, start=1):
        anchor = block.get("source_anchor")
        if not isinstance(anchor, dict):
            anchor = {}
        attributes = block.get("attributes")
        if not isinstance(attributes, dict):
            attributes = {}
        chunk: dict[str, Any] = {
            "id": f"raw_b{index:04d}",
            "type": str(block.get("type") or "paragraph"),
            "text": block.get("text"),
            "page": anchor.get("page"),
            "bbox": anchor.get("bbox"),
            "metadata": {
                "upstream_provider": provider_used,
                "source_attributes": attributes,
            },
        }
        rows = attributes.get("rows")
        if chunk["type"] == "table" and isinstance(rows, list):
            chunk["rows"] = rows
        chunks.append(chunk)
    return chunks


def convert_raw_document(
    input_path: Path | str,
    *,
    provider: str,
    provider_runner: ProviderRunner | None = None,
    allow_fallback: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Convert one local document without importing optional providers eagerly."""
    path = Path(input_path)
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported_provider:{provider}")
    if not path.is_file():
        raise ValueError(f"input_not_found:{path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported_format:{path.suffix.lower()}")

    source_bytes = path.read_bytes()
    if not source_bytes:
        raise ValueError("empty_input")
    if len(source_bytes) > max_bytes:
        raise ValueError(f"input_too_large:{len(source_bytes)}")

    runner = provider_runner or (
        _run_docling if provider == "docling" else _run_unstructured
    )
    fallback_used = False
    warnings: list[str] = []
    try:
        extraction = _coerce_extraction(runner(path), default_method=provider)
    except (ImportError, ModuleNotFoundError) as exc:
        if not allow_fallback:
            raise RuntimeError(f"optional_provider_unavailable:{provider}") from exc
        fallback_used = True
        warnings.append(f"optional_provider_unavailable:{provider}")
        extraction = _coerce_extraction(
            _fallback_extract(path, source_bytes),
            default_method="deterministic_fallback",
        )

    digest = hashlib.sha256(source_bytes).hexdigest()
    provider_used = extraction["method"]
    chunks = _external_chunks(
        extraction["blocks"],
        provider_used=provider_used,
    )
    title = extraction["title"] or path.stem
    external_uir = {
        "id": f"raw_{digest[:16]}",
        "title": title,
        "source": {
            "provider": provider_used,
            "original_name": path.name,
            "source_sha256": digest,
        },
        "metadata": {
            "raw_upstream_provider": provider_used,
            "original_name": path.name,
            "source_sha256": digest,
            "extraction_metadata": extraction["metadata"],
        },
        "chunks": chunks,
    }
    report = {
        "status": "passed",
        "provider_requested": provider,
        "provider_used": provider_used,
        "fallback_used": fallback_used,
        "source_file": path.name,
        "source_sha256": digest,
        "source_size_bytes": len(source_bytes),
        "block_count": len(chunks),
        "auto_imported": False,
        "task_created": False,
        "llm_auto_accepted_count": 0,
        "secret_leak_count": 0,
        "warnings": warnings,
    }
    return {"external_uir": external_uir, "report": report}


def run_cli(provider: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"Convert a local document with optional {provider} support."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", "--output", dest="output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--no-fallback", action="store_true")
    args = parser.parse_args(argv)

    result = convert_raw_document(
        args.input,
        provider=provider,
        allow_fallback=not args.no_fallback,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result["external_uir"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.report.write_text(
        json.dumps(result["report"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "report": str(args.report),
                "provider_used": result["report"]["provider_used"],
                "block_count": result["report"]["block_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0

