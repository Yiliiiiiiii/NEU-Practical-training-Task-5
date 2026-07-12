"""Shared deterministic inputs for Topic 5 reliability evaluators."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def example_request(name: str = "announcement") -> dict[str, Any]:
    filename = f"{name}_convert_request.json"
    return load_json(ROOT / "examples" / "topic5_inline" / filename)


def performance_request(block_count: int) -> dict[str, Any]:
    """Build a mixed-content request with exactly ``block_count`` blocks."""
    if block_count < 1:
        raise ValueError("block_count must be positive")
    request = copy.deepcopy(example_request())
    request.pop("output_assertions", None)
    request["uir"]["doc_id"] = f"performance-{block_count}"
    request["uir"]["metadata"] = {
        "source": "topic5-performance-v1",
        "language": "zh-CN",
        "document_title": f"Reliability fixture {block_count}",
        "fixture_block_count": block_count,
    }
    blocks: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    for index in range(block_count):
        block_id = f"b{index + 1:05d}"
        kind = index % 20
        attributes: dict[str, Any] = {"candidate_label": f"candidate-{index % 7}"}
        if kind == 0:
            block_type = "heading"
            text = f"Section {index // 20 + 1}"
            level = 2
            attributes["field_name"] = "title"
        elif kind == 1:
            block_type = "paragraph"
            text = "Issuer: Reliability Office"
            level = None
            attributes["field_name"] = "issuer"
        elif kind == 2:
            block_type = "paragraph"
            text = "Publish date: 2026-07-12"
            level = None
            attributes["field_name"] = "publish_date"
        elif kind == 3:
            block_type = "list_item"
            text = f"Checklist item {index}: preserve source linkage"
            level = None
        elif kind == 4:
            block_type = "table"
            text = "metric | value\nblocks | deterministic"
            level = None
        else:
            block_type = "paragraph"
            text = f"Body paragraph {index} with deterministic benchmark content."
            level = None
            if kind == 5:
                attributes["field_name"] = "body"
        block: dict[str, Any] = {
            "block_id": block_id,
            "type": block_type,
            "text": text,
            "attributes": attributes,
        }
        if level is not None:
            block["level"] = level
        blocks.append(block)
        if index % 250 == 0:
            entities.append(
                {
                    "mention": f"Reliability Office {index // 250}",
                    "canonical_name": "Reliability Office",
                    "entity_type": "organization",
                    "normalized_id": f"org:reliability:{index // 250}",
                    "link_status": "linked",
                    "confidence": 1.0,
                    "source_block_ids": [block_id],
                    "source_agent": "topic5-performance-fixture",
                    "evidence": {"fixture": True},
                }
            )
    request["uir"]["blocks"] = blocks
    request["uir"]["entities"] = entities
    request["uir"]["assets"] = []
    request["uir"]["normalization_records"] = []
    request["content_organization"]["summary"] = {
        "chunk_mode": "deterministic",
        "document_mode": "none",
    }
    request["options"]["chunk_size"] = 1200
    request["options"]["enable_llm_fallback"] = False
    return request


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
