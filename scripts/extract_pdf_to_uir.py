"""Extract UIR-compatible blocks from PDFs that contain a usable text layer."""

from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path
from statistics import median
from typing import Any

import fitz
from real_world_uir_common import ExtractionResult

MIN_TEXT_CHARACTERS = 40


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_pdf(pdf_bytes: bytes) -> ExtractionResult:
    try:
        document = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    except Exception as exc:
        return ExtractionResult(
            title="",
            blocks=[],
            status="rejected",
            reason=f"invalid_pdf:{type(exc).__name__}",
            extraction_method="pymupdf_text",
        )

    lines: list[dict[str, Any]] = []
    page_text_lengths: list[int] = []
    try:
        for page_index, page in enumerate(document):
            page_text = normalize_text(page.get_text("text"))
            page_text_lengths.append(len(page_text))
            page_dict = page.get_text("dict")
            for raw_block in page_dict.get("blocks", []):
                if raw_block.get("type") != 0:
                    continue
                for raw_line in raw_block.get("lines", []):
                    spans = raw_line.get("spans", [])
                    text = normalize_text(
                        "".join(str(span.get("text", "")) for span in spans)
                    )
                    if not text:
                        continue
                    sizes = [float(span.get("size", 0.0)) for span in spans]
                    fonts = " ".join(
                        str(span.get("font", "")) for span in spans
                    ).lower()
                    lines.append(
                        {
                            "text": text,
                            "page": page_index + 1,
                            "bbox": [
                                float(value) for value in raw_line.get("bbox", [])
                            ],
                            "font_size": max(sizes, default=0.0),
                            "bold": "bold" in fonts,
                        }
                    )
    finally:
        document.close()

    if sum(page_text_lengths) < MIN_TEXT_CHARACTERS or not lines:
        return ExtractionResult(
            title="",
            blocks=[],
            metadata={"page_text_lengths": page_text_lengths},
            status="skipped",
            reason="unsupported_scanned_pdf",
            extraction_method="pymupdf_text",
        )

    common_size = median(line["font_size"] for line in lines if line["font_size"] > 0)
    largest_size = max(line["font_size"] for line in lines)
    title_line = next(
        (
            line
            for line in lines
            if line["font_size"] == largest_size and len(line["text"]) <= 160
        ),
        lines[0],
    )
    blocks: list[dict[str, Any]] = []
    for line in lines:
        is_heading = len(line["text"]) <= 160 and (
            line is title_line
            or line["font_size"] >= max(14.0, common_size * 1.2)
            or (line["bold"] and line["font_size"] > common_size)
        )
        block: dict[str, Any] = {
            "type": "heading" if is_heading else "paragraph",
            "text": line["text"],
            "source_anchor": {
                "page": line["page"],
                "bbox": line["bbox"] if len(line["bbox"]) == 4 else None,
            },
            "attributes": {
                "font_size": line["font_size"],
                "font_bold": line["bold"],
            },
        }
        if is_heading:
            block["level"] = 1 if line is title_line else 2
        blocks.append(block)

    return ExtractionResult(
        title=title_line["text"],
        blocks=blocks,
        metadata={
            "page_count": len(page_text_lengths),
            "page_text_lengths": page_text_lengths,
        },
        extraction_method="pymupdf_text",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract_pdf(args.input.read_bytes())
    payload = {
        "title": result.title,
        "blocks": result.blocks,
        "metadata": result.metadata,
        "status": result.status,
        "reason": result.reason,
        "extraction_method": result.extraction_method,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
