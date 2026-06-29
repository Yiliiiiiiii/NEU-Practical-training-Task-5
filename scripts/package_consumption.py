"""Helpers for downstream consumers of SchemaPack output packages."""

import hashlib
import json
import re
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


class PackageReadError(ValueError):
    """Raised when an output package cannot be consumed safely."""


@contextmanager
def resolved_package_dir(package_path: Path) -> Iterator[Path]:
    path = package_path.resolve()
    if path.is_dir():
        yield path
        return

    if path.is_file() and path.suffix.lower() == ".zip":
        with TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(path) as archive:
                archive.extractall(temp_dir)
            yield Path(temp_dir)
        return

    raise PackageReadError(f"package must be a directory or .zip file: {package_path}")


def load_manifest(package_dir: Path) -> dict[str, Any]:
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PackageReadError("manifest.json is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageReadError(f"manifest.json is invalid: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PackageReadError("manifest.json must be a JSON object")
    return manifest


def load_metadata(package_dir: Path) -> dict[str, Any]:
    metadata_path = package_dir / "metadata.json"
    if not metadata_path.is_file():
        return {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageReadError(f"metadata.json is invalid: {exc}") from exc
    if not isinstance(metadata, dict):
        raise PackageReadError("metadata.json must be a JSON object")
    return metadata


def validate_manifest_files(package_dir: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise PackageReadError("manifest.files must be a list")

    for file_info in files:
        if not isinstance(file_info, dict):
            raise PackageReadError("manifest file entries must be JSON objects")
        relative_path = file_info.get("path")
        expected_sha256 = file_info.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            raise PackageReadError("manifest file entry is missing path")
        if not isinstance(expected_sha256, str) or not expected_sha256:
            raise PackageReadError(f"manifest entry {relative_path} is missing sha256")

        path = package_dir / relative_path
        if file_info.get("required", True) and not path.is_file():
            raise PackageReadError(f"required file is missing: {relative_path}")
        if path.is_file() and sha256_file(path) != expected_sha256:
            raise PackageReadError(f"checksum mismatch: {relative_path}")


def load_chunks(package_dir: Path) -> list[dict[str, Any]]:
    chunks_path = package_dir / "chunks.jsonl"
    if not chunks_path.is_file():
        raise PackageReadError("chunks.jsonl is missing")

    chunks: list[dict[str, Any]] = []
    for line_number, line in enumerate(chunks_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PackageReadError(f"chunks.jsonl line {line_number} is invalid: {exc}") from exc
        if not isinstance(chunk, dict):
            raise PackageReadError(f"chunks.jsonl line {line_number} must be a JSON object")
        chunks.append(chunk)

    if not chunks:
        raise PackageReadError("chunks.jsonl does not contain any chunks")
    return chunks


def read_validated_package(package_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with resolved_package_dir(package_path) as package_dir:
        manifest = load_manifest(package_dir)
        validate_manifest_files(package_dir, manifest)
        manifest["_metadata"] = load_metadata(package_dir)
        chunks = load_chunks(package_dir)
        return manifest, chunks


def filter_chunks_by_granularity(
    chunks: list[dict[str, Any]],
    granularity: str,
) -> list[dict[str, Any]]:
    if granularity == "all":
        return chunks
    return [chunk for chunk in chunks if chunk.get("granularity") == granularity]


def search_chunks(chunks: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    if not chunks:
        return None

    terms = extract_terms(query)
    if not terms:
        return {**chunks[0], "_score": 0}

    best_chunk: dict[str, Any] | None = None
    best_score = 0
    for chunk in chunks:
        searchable = chunk_search_text(chunk)
        score = sum(searchable.count(term.lower()) for term in terms)
        if score > best_score:
            best_chunk = chunk
            best_score = score

    if best_chunk is None:
        return None
    return {**best_chunk, "_score": best_score}


def extract_terms(text: str) -> list[str]:
    return [
        item.lower()
        for item in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}|[\u4e00-\u9fff]{2,8}", text)
    ]


def chunk_search_text(chunk: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("text", "summary"):
        value = chunk.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("keywords", "title_path", "source_block_ids"):
        value = chunk.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    tags = chunk.get("tags")
    if isinstance(tags, dict):
        for value in tags.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
    return "\n".join(parts).lower()


def chunk_source_linked(chunk: dict[str, Any]) -> bool:
    return bool(chunk.get("source_links")) or bool(chunk.get("source_block_ids"))


def training_metadata(manifest: dict[str, Any], chunk: dict[str, Any]) -> dict[str, Any]:
    generator = manifest.get("generator") if isinstance(manifest.get("generator"), dict) else {}
    metadata = manifest.get("_metadata") if isinstance(manifest.get("_metadata"), dict) else {}
    return {
        "doc_id": chunk.get("doc_id") or manifest.get("doc_id"),
        "task_id": chunk.get("task_id") or manifest.get("task_id"),
        "package_id": manifest.get("package_id"),
        "schema_id": metadata.get("schema_id") or generator.get("schema_id"),
        "schema_version": metadata.get("schema_version") or generator.get("schema_version"),
        "template_id": metadata.get("template_id") or generator.get("template_id"),
        "template_version": metadata.get("template_version") or generator.get("template_version"),
        "granularity": chunk.get("granularity"),
        "parent_chunk_id": chunk.get("parent_chunk_id"),
        "tags": chunk.get("tags", {}),
        "keywords": chunk.get("keywords", []),
        "summary": chunk.get("summary", ""),
        "title_path": chunk.get("title_path", []),
        "source_block_ids": chunk.get("source_block_ids", []),
        "source_links": chunk.get("source_links", []),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
