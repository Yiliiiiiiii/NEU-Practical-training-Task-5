"""Download bounded official-public source files listed in the real-world manifest."""

from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from real_world_uir_common import (
    dataset_paths,
    read_json,
    sha256_bytes,
    write_json_atomic,
)

DEFAULT_MAX_BYTES = 20 * 1024 * 1024
VALID_FORMATS = {"html", "pdf", "docx", "txt"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _valid_source_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _write_bytes_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _failure(item: dict[str, Any], reason: str, message: str | None = None) -> None:
    item["status"] = "failed"
    item["failure_reason"] = reason
    if message:
        item["failure_message"] = message[:300]
    else:
        item.pop("failure_message", None)


def _looks_like_login_page(content: bytes, content_type: str) -> bool:
    if "html" not in content_type.lower():
        return False
    sample = content[:200_000].decode("utf-8", errors="ignore").lower()
    markers = ("验证码", "请输入密码", "login required", "verify you are human")
    return any(marker in sample for marker in markers)


def _content_type_matches(source_format: str, content_type: str, content: bytes) -> bool:
    mime_type = content_type.lower().split(";", 1)[0].strip()
    if source_format == "html":
        return mime_type in {"text/html", "application/xhtml+xml"} or b"<html" in content[
            :4096
        ].lower()
    if source_format == "pdf":
        return mime_type == "application/pdf" or content.startswith(b"%PDF")
    if source_format == "docx":
        return mime_type in {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        } and content.startswith(b"PK")
    if source_format == "txt":
        return mime_type.startswith("text/")
    return False


def collect_manifest(
    *,
    manifest_path: Path,
    cache_dir: Path,
    session: Any | None = None,
    timeout: float = 20.0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    source_ids: set[str] | None = None,
    retrieved_at_factory: Callable[[], str] = _now,
) -> dict[str, int]:
    manifest = read_json(manifest_path)
    items = manifest.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest items must be a list")
    client = session or requests.Session()
    summary = {"fetched": 0, "skipped": 0, "failed": 0}

    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id", ""))
        if source_ids and source_id not in source_ids:
            continue
        status = item.get("status")
        cached_path = cache_dir / str(item.get("cached_path", ""))
        cache_exists = bool(item.get("cached_path")) and cached_path.is_file()
        if status in {"fetched", "extracted"} and cache_exists:
            continue
        if status not in {"planned", "failed", "fetched", "extracted"}:
            continue

        url = str(item.get("source_url", ""))
        source_format = str(item.get("source_format", "")).lower()
        if not _valid_source_url(url):
            _failure(item, "invalid_source_url")
            summary["failed"] += 1
            continue
        if source_format not in VALID_FORMATS:
            _failure(item, "unsupported_source_format")
            summary["failed"] += 1
            continue

        try:
            response = client.get(
                url,
                timeout=timeout,
                stream=True,
                allow_redirects=True,
                headers={"User-Agent": "SchemaPackRealWorldDataset/0.1"},
            )
            item["http_status"] = int(response.status_code)
            if not 200 <= response.status_code < 300:
                _failure(item, "http_error", f"HTTP {response.status_code}")
                summary["failed"] += 1
                continue
            declared_size = int(response.headers.get("Content-Length", "0") or 0)
            if declared_size > max_bytes:
                _failure(item, "content_too_large")
                summary["failed"] += 1
                continue

            chunks: list[bytes] = []
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                downloaded_size += len(chunk)
                if downloaded_size > max_bytes:
                    raise ValueError("content_too_large")
                chunks.append(chunk)
            content = b"".join(chunks)
            content_type = str(response.headers.get("Content-Type", ""))
            item["content_type"] = content_type
            if not _content_type_matches(source_format, content_type, content):
                _failure(item, "content_type_mismatch")
                summary["failed"] += 1
                continue
            if _looks_like_login_page(content, content_type):
                item["status"] = "skipped"
                item["skip_reason"] = "login_or_verification_required"
                summary["skipped"] += 1
                continue

            filename = f"{source_id}.{source_format}"
            _write_bytes_atomic(cache_dir / filename, content)
            item.update(
                {
                    "status": "fetched",
                    "cached_path": filename,
                    "retrieved_at": retrieved_at_factory(),
                    "source_sha256": sha256_bytes(content),
                    "downloaded_bytes": len(content),
                }
            )
            item.pop("failure_reason", None)
            item.pop("failure_message", None)
            item.pop("skip_reason", None)
            summary["fetched"] += 1
        except ValueError as exc:
            reason = str(exc) if str(exc) == "content_too_large" else "download_error"
            _failure(item, reason)
            summary["failed"] += 1
        except requests.RequestException as exc:
            _failure(item, "http_error", str(exc))
            summary["failed"] += 1
        except Exception as exc:
            _failure(item, "download_error", f"{type(exc).__name__}: {exc}")
            summary["failed"] += 1

    write_json_atomic(manifest_path, manifest)
    return summary


def main() -> None:
    paths = dataset_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=paths["manifest"])
    parser.add_argument("--cache-dir", type=Path, default=paths["cache"])
    parser.add_argument("--source-id", action="append", dest="source_ids")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()
    summary = collect_manifest(
        manifest_path=args.manifest,
        cache_dir=args.cache_dir,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
        source_ids=set(args.source_ids) if args.source_ids else None,
    )
    print(summary)


if __name__ == "__main__":
    main()
