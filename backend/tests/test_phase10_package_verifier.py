import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from app.verifiers.package_verifier import verify_package_zip


def _manifest_entry(path: str, raw: bytes, media_type: str | None = None) -> dict:
    if media_type is None:
        media_type = "application/json" if path.endswith(".json") else "text/plain"
    return {
        "path": path,
        "required": True,
        "media_type": media_type,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "role": path.rsplit(".", 1)[0],
    }


def _write_package(
    tmp_path: Path,
    payloads: dict[str, bytes],
    *,
    manifest_entries: list[dict] | None = None,
    extra_entries: dict[str, bytes] | None = None,
) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": "1.0",
        "package_id": "pkg_phase10",
        "package_version": "10.0.0-test",
        "task_id": "task_phase10",
        "doc_id": "doc_phase10",
        "created_at": "2026-06-23T00:00:00+00:00",
        "files": (
            manifest_entries
            if manifest_entries is not None
            else [_manifest_entry(path, raw) for path, raw in sorted(payloads.items())]
        ),
        "generator": {"name": "test", "version": "10"},
    }
    zip_path = tmp_path / "standard_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, raw in payloads.items():
            archive.writestr(path, raw)
        for path, raw in (extra_entries or {}).items():
            archive.writestr(path, raw)
        archive.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))
    return zip_path


def _valid_payloads() -> dict[str, bytes]:
    return {
        "content.json": b'{"content_version":"1.1","data":{"title":"ok"}}',
        "content.md": b"# ok\n",
        "chunks.json": b'{"chunks":[]}',
    }


def _issue_codes(zip_path: Path, *, max_json_bytes: int = 5_000_000) -> set[str]:
    report = verify_package_zip(zip_path, max_json_bytes=max_json_bytes)
    assert not report.passed
    return {issue.code for issue in report.issues}


def test_external_package_verifier_accepts_valid_zip(tmp_path):
    zip_path = _write_package(tmp_path, _valid_payloads())

    report = verify_package_zip(zip_path)

    assert report.passed is True
    assert report.zip_path == str(zip_path)
    assert report.zip_sha256 == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert report.summary == {
        "manifest_files": 3,
        "zip_entries": 4,
        "verified_payloads": 3,
        "total_payload_bytes": sum(len(raw) for raw in _valid_payloads().values()),
    }
    assert report.issues == []


@pytest.mark.parametrize(
    ("payloads", "manifest_entries", "extra_entries", "expected_code"),
    [
        (
            {"../evil.json": b"{}"},
            [_manifest_entry("../evil.json", b"{}")],
            None,
            "unsafe_zip_path",
        ),
        (
            {"bad\\name.json": b"{}"},
            [_manifest_entry("bad\\name.json", b"{}")],
            None,
            "unsafe_zip_path",
        ),
        (
            _valid_payloads(),
            [_manifest_entry("manifest.json", b"{}")],
            None,
            "manifest_self_reference",
        ),
        (
            _valid_payloads(),
            [_manifest_entry(path, raw) for path, raw in _valid_payloads().items()],
            {"unexpected.json": b"{}"},
            "zip_entry_set_mismatch",
        ),
        (
            {"content.json": b"{}"},
            [_manifest_entry("content.json", b"{}"), _manifest_entry("missing.json", b"{}")],
            None,
            "zip_entry_set_mismatch",
        ),
    ],
)
def test_external_package_verifier_rejects_entry_set_and_path_errors(
    tmp_path,
    payloads,
    manifest_entries,
    extra_entries,
    expected_code,
):
    zip_path = _write_package(
        tmp_path,
        payloads,
        manifest_entries=manifest_entries,
        extra_entries=extra_entries,
    )

    assert expected_code in _issue_codes(zip_path)


def test_external_package_verifier_rejects_payload_byte_and_hash_mismatch(tmp_path):
    raw = b'{"ok":true}'
    wrong_bytes = _manifest_entry("content.json", raw)
    wrong_bytes["bytes"] = len(raw) + 1
    byte_zip = _write_package(
        tmp_path,
        {"content.json": raw},
        manifest_entries=[wrong_bytes],
    )

    wrong_hash = _manifest_entry("content.json", raw)
    wrong_hash["sha256"] = "0" * 64
    hash_zip = _write_package(
        tmp_path / "hash",
        {"content.json": raw},
        manifest_entries=[wrong_hash],
    )

    assert "payload_bytes_mismatch" in _issue_codes(byte_zip)
    assert "payload_sha256_mismatch" in _issue_codes(hash_zip)


def test_external_package_verifier_rejects_invalid_and_oversized_json(tmp_path):
    invalid_zip = _write_package(tmp_path, {"content.json": b"{not-json"})
    oversized_zip = _write_package(tmp_path / "oversized", {"content.json": b'{"abc":1}'})

    assert "invalid_json" in _issue_codes(invalid_zip)
    assert "json_too_large" in _issue_codes(oversized_zip, max_json_bytes=3)


def test_external_package_verifier_rejects_missing_manifest(tmp_path):
    zip_path = tmp_path / "missing_manifest.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("content.json", b"{}")

    assert "missing_manifest" in _issue_codes(zip_path)


def test_package_verifier_cli_outputs_json_and_nonzero_on_failure(tmp_path):
    zip_path = _write_package(tmp_path, {"content.json": b"{not-json"})
    backend_dir = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-m", "app.tools.package_verifier", str(zip_path)],
        cwd=backend_dir,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    body = json.loads(result.stdout)
    assert body["passed"] is False
    assert {issue["code"] for issue in body["issues"]} == {"invalid_json"}
