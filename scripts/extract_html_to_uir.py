"""Extract deterministic UIR-compatible blocks from a public HTML document."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag
from real_world_uir_common import ExtractionResult

BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "table")
REMOVED_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "iframe",
    "svg",
)
METADATA_LABELS = {
    "发布日期",
    "发布机构",
    "发文机关",
    "文号",
    "项目编号",
    "采购人",
    "会议时间",
    "会议地点",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _content_root(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    for selector in (
        "article",
        "main",
        "#content",
        "#zoom",
        "#ivs_content",
        ".article",
        ".article-content",
        ".xxgk_content_nr",
        ".xwnr_content",
        ".content",
        ".TRS_Editor",
    ):
        candidate = soup.select_one(selector)
        if isinstance(candidate, Tag):
            return candidate
    return soup.body or soup


def _extract_table(tag: Tag) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in tag.find_all("tr"):
        cells = [
            normalize_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(("th", "td"), recursive=False)
        ]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        if len(cells) == 1:
            rows.append({"field": cells[0], "value": ""})
        else:
            rows.append({"field": cells[0], "value": " | ".join(cells[1:])})
    return rows


def _is_layout_table(tag: Tag) -> bool:
    if str(tag.get("role", "")).lower() == "presentation":
        return True
    return len(tag.find_all(("h1", "h2", "h3", "h4", "h5", "h6", "p"))) >= 2


def _extract_metadata(text: str, metadata: dict[str, Any]) -> None:
    match = re.match(r"^([^：:]{2,12})[：:]\s*(.+)$", text)
    if match and match.group(1) in METADATA_LABELS:
        metadata[match.group(1)] = match.group(2).strip()


def extract_html(
    html_bytes: bytes,
    *,
    source_url: str,
    encoding: str | None = None,
) -> ExtractionResult:
    soup = BeautifulSoup(
        html_bytes,
        "lxml",
        from_encoding=encoding,
    )
    for tag in soup.find_all(REMOVED_TAGS):
        tag.decompose()

    root = _content_root(soup)
    blocks: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"source_url": source_url}
    seen_text: set[str] = set()

    for tag in root.find_all(BLOCK_TAGS):
        if tag.find_parent(("ul", "ol")) is not None:
            continue
        parent_table = tag.find_parent("table")
        if parent_table is not None and not _is_layout_table(parent_table):
            continue
        name = tag.name.lower()
        if name.startswith("h"):
            text = normalize_text(tag.get_text(" ", strip=True))
            if text and text not in seen_text:
                blocks.append(
                    {
                        "type": "heading",
                        "level": int(name[1]),
                        "text": text,
                        "attributes": {"html_tag": name},
                    }
                )
                seen_text.add(text)
        elif name == "p":
            text = normalize_text(tag.get_text(" ", strip=True))
            if text and text not in seen_text:
                blocks.append(
                    {
                        "type": "paragraph",
                        "text": text,
                        "attributes": {"html_tag": name},
                    }
                )
                seen_text.add(text)
                _extract_metadata(text, metadata)
        elif name in {"ul", "ol"}:
            items = [
                normalize_text(item.get_text(" ", strip=True))
                for item in tag.find_all("li", recursive=False)
            ]
            items = [item for item in items if item]
            if items:
                blocks.append(
                    {
                        "type": "list",
                        "text": None,
                        "attributes": {"items": items, "ordered": name == "ol"},
                    }
                )
                seen_text.update(items)
        elif name == "table":
            if _is_layout_table(tag):
                continue
            rows = _extract_table(tag)
            if rows:
                blocks.append(
                    {
                        "type": "table",
                        "text": None,
                        "attributes": {"rows": rows},
                    }
                )
                seen_text.update(row["field"] for row in rows)
                seen_text.update(row["value"] for row in rows)

    if len(blocks) < 3:
        for raw_text in root.stripped_strings:
            text = normalize_text(raw_text)
            if (
                len(text) < 2
                or text in seen_text
                or text.strip("[]【】 ") in {"打印", "来源"}
            ):
                continue
            blocks.append(
                {
                    "type": "paragraph",
                    "text": text,
                    "attributes": {"fallback": "text_node"},
                }
            )
            seen_text.add(text)
            _extract_metadata(text, metadata)

    title_block = next(
        (block for block in blocks if block["type"] == "heading"),
        None,
    )
    page_title = normalize_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    title = str(title_block["text"]) if title_block else page_title
    if not blocks or not title:
        return ExtractionResult(
            title=title,
            blocks=[],
            metadata=metadata,
            status="rejected",
            reason="empty_extraction",
            extraction_method="beautifulsoup_lxml",
        )

    return ExtractionResult(
        title=title,
        blocks=blocks,
        metadata=metadata,
        extraction_method="beautifulsoup_lxml",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = extract_html(args.input.read_bytes(), source_url=args.source_url)
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
