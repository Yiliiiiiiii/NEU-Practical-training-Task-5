"""Shared primitives for building the real-world UIR evaluation dataset."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "examples" / "real_world"
MAX_UIR_BLOCKS = 250
VALID_DOC_TYPES = {
    "policy_doc",
    "procurement_doc",
    "contract_doc",
    "meeting_doc",
    "general_doc",
}


@dataclass
class ExtractionResult:
    title: str
    blocks: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "extracted"
    reason: str | None = None
    extraction_method: str = ""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(value: str, fallback: str = "document") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def make_block_id(doc_id: str, index: int) -> str:
    return f"{doc_id}_b{index:03d}"


def build_uir(
    *,
    source: dict[str, Any],
    title: str,
    blocks: list[dict[str, Any]],
    source_bytes: bytes,
    retrieved_at: str,
    source_format: str,
    extraction_method: str,
    extracted_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc_id = str(source["source_id"])
    doc_type = str(source["doc_type"])
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"unsupported doc_type: {doc_type}")

    normalized_blocks: list[dict[str, Any]] = []
    for index, source_block in enumerate(blocks[:MAX_UIR_BLOCKS], start=1):
        block = {
            "block_id": make_block_id(doc_id, index),
            "type": str(source_block["type"]),
            "level": source_block.get("level"),
            "text": source_block.get("text"),
            "source_anchor": source_block.get("source_anchor"),
            "attributes": dict(source_block.get("attributes", {})),
        }
        normalized_blocks.append(block)

    metadata = {
        "title": title,
        "标题": title,
        "doc_type": doc_type,
        "domain": doc_type,
        "language": str(source.get("language", "zh-CN")),
        "source_url": str(source["source_url"]),
        "source_site": str(source["source_site"]),
        "retrieved_at": retrieved_at,
        "source_format": source_format,
        "source_sha256": sha256_bytes(source_bytes),
        "extraction_method": extraction_method,
        "extraction_version": "0.1.0",
    }
    if extracted_metadata:
        metadata.update(extracted_metadata)
    metadata["extracted_block_count"] = len(blocks)
    metadata["extraction_truncated"] = len(blocks) > MAX_UIR_BLOCKS

    return {
        "uir_version": "1.0",
        "doc_id": doc_id,
        "source": {
            "source_type": "real_world_public_document",
            "source_name": doc_id,
            "upstream_agents": ["real_world_uir_builder"],
        },
        "metadata": metadata,
        "blocks": normalized_blocks,
        "assets": [],
        "normalization_records": [
            {
                "normalized": True,
                "method": extraction_method,
                "source_sha256": metadata["source_sha256"],
            }
        ],
    }


def dataset_paths(dataset_dir: Path = DATASET_DIR) -> dict[str, Path]:
    return {
        "root": dataset_dir,
        "manifest": dataset_dir / "sources" / "source_manifest.json",
        "cache": dataset_dir / "raw_cache",
        "uir": dataset_dir / "uir",
        "reports": dataset_dir / "reports",
    }


def markdown_cell(value: Any) -> str:
    return str(value).replace("|", r"\|").replace("\n", "<br>")
