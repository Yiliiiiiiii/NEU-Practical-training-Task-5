"""Extract UIR-compatible blocks from a DOCX document."""

from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from real_world_uir_common import ExtractionResult


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _table_rows(table: Table) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in table.rows:
        cells = [normalize_text(cell.text) for cell in row.cells]
        if not any(cells):
            continue
        rows.append(
            {
                "field": cells[0],
                "value": " | ".join(cells[1:]) if len(cells) > 1 else "",
            }
        )
    return rows


def extract_docx(docx_bytes: bytes) -> ExtractionResult:
    try:
        document = Document(io.BytesIO(docx_bytes))
    except Exception as exc:
        return ExtractionResult(
            title="",
            blocks=[],
            status="rejected",
            reason=f"invalid_docx:{type(exc).__name__}",
            extraction_method="python_docx",
        )

    blocks: list[dict[str, Any]] = []
    title = ""
    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            text = normalize_text(item.text)
            if not text:
                continue
            style_name = item.style.name if item.style is not None else ""
            heading_match = re.match(r"^Heading\s+([1-6])$", style_name, re.IGNORECASE)
            if heading_match:
                level = int(heading_match.group(1))
                blocks.append(
                    {
                        "type": "heading",
                        "level": level,
                        "text": text,
                        "attributes": {"docx_style": style_name},
                    }
                )
                if not title:
                    title = text
            else:
                blocks.append(
                    {
                        "type": "paragraph",
                        "text": text,
                        "attributes": {"docx_style": style_name},
                    }
                )
                if not title:
                    title = text
        elif isinstance(item, Table):
            rows = _table_rows(item)
            if rows:
                blocks.append(
                    {
                        "type": "table",
                        "text": None,
                        "attributes": {"rows": rows},
                    }
                )

    if not blocks or not title:
        return ExtractionResult(
            title=title,
            blocks=[],
            status="rejected",
            reason="empty_extraction",
            extraction_method="python_docx",
        )
    return ExtractionResult(
        title=title,
        blocks=blocks,
        metadata={},
        extraction_method="python_docx",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract_docx(args.input.read_bytes())
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
