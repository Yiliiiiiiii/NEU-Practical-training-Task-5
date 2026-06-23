from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.package import Manifest


class PackageVerifierIssue(StrictBaseModel):
    code: str
    message: str
    path: str | None = None


class PackageVerifierReport(StrictBaseModel):
    passed: bool
    zip_path: str
    zip_sha256: str | None = None
    summary: dict[str, int] = Field(default_factory=dict)
    issues: list[PackageVerifierIssue] = Field(default_factory=list)


def verify_package_zip(
    zip_path: str | Path,
    *,
    max_json_bytes: int = 5_000_000,
) -> PackageVerifierReport:
    path = Path(zip_path)
    issues: list[PackageVerifierIssue] = []
    summary = {
        "manifest_files": 0,
        "zip_entries": 0,
        "verified_payloads": 0,
        "total_payload_bytes": 0,
    }
    zip_sha256 = _sha256(path) if path.is_file() else None

    if not path.is_file():
        return PackageVerifierReport(
            passed=False,
            zip_path=str(path),
            zip_sha256=zip_sha256,
            summary=summary,
            issues=[_issue("zip_not_found", "package ZIP was not found")],
        )

    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            summary["zip_entries"] = len(names)

            for name in names:
                if _unsafe_zip_name(name):
                    issues.append(_issue("unsafe_zip_path", "ZIP entry path is unsafe", name))

            if "manifest.json" not in names:
                issues.append(_issue("missing_manifest", "manifest.json is missing"))
                return _report(path, zip_sha256, summary, issues)

            manifest_raw = archive.read("manifest.json")
            try:
                manifest_data = json.loads(manifest_raw.decode("utf-8"))
                manifest = Manifest.model_validate(manifest_data)
            except Exception as exc:
                issues.append(_issue(
                    "invalid_manifest",
                    f"manifest.json is not a valid manifest: {exc}",
                    "manifest.json",
                ))
                return _report(path, zip_sha256, summary, issues)

            summary["manifest_files"] = len(manifest.files)
            manifest_paths = [entry.path for entry in manifest.files]
            for manifest_path in manifest_paths:
                if manifest_path == "manifest.json":
                    issues.append(_issue(
                        "manifest_self_reference",
                        "manifest must not include itself",
                        manifest_path,
                    ))
                if _unsafe_zip_name(manifest_path):
                    issues.append(_issue(
                        "unsafe_zip_path",
                        "manifest file path is unsafe",
                        manifest_path,
                    ))

            expected = set(manifest_paths) | {"manifest.json"}
            actual = set(names)
            if actual != expected:
                issues.append(_issue(
                    "zip_entry_set_mismatch",
                    "ZIP entries do not exactly match manifest payload plus manifest.json",
                ))

            for entry in manifest.files:
                if entry.path not in actual or _unsafe_zip_name(entry.path):
                    continue
                raw = archive.read(entry.path)
                summary["verified_payloads"] += 1
                summary["total_payload_bytes"] += len(raw)
                if len(raw) != entry.bytes:
                    issues.append(_issue(
                        "payload_bytes_mismatch",
                        f"payload byte count {len(raw)} does not match manifest {entry.bytes}",
                        entry.path,
                    ))
                if hashlib.sha256(raw).hexdigest() != entry.sha256:
                    issues.append(_issue(
                        "payload_sha256_mismatch",
                        "payload SHA-256 does not match manifest",
                        entry.path,
                    ))
                if _is_json_payload(entry.path, entry.media_type):
                    if len(raw) > max_json_bytes:
                        issues.append(_issue(
                            "json_too_large",
                            f"JSON payload exceeds {max_json_bytes} bytes",
                            entry.path,
                        ))
                    else:
                        try:
                            json.loads(raw.decode("utf-8"))
                        except Exception as exc:
                            issues.append(_issue(
                                "invalid_json",
                                f"JSON payload is invalid: {exc}",
                                entry.path,
                            ))
    except zipfile.BadZipFile:
        issues.append(_issue("invalid_zip", "file is not a valid ZIP archive"))

    return _report(path, zip_sha256, summary, issues)


def _report(
    path: Path,
    zip_sha256: str | None,
    summary: dict[str, int],
    issues: list[PackageVerifierIssue],
) -> PackageVerifierReport:
    return PackageVerifierReport(
        passed=not issues,
        zip_path=str(path),
        zip_sha256=zip_sha256,
        summary=summary,
        issues=issues,
    )


def _issue(code: str, message: str, path: str | None = None) -> PackageVerifierIssue:
    return PackageVerifierIssue(code=code, message=message, path=path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unsafe_zip_name(name: str) -> bool:
    rel_path = Path(name)
    return (
        not name
        or "\\" in name
        or name.startswith("/")
        or rel_path.is_absolute()
        or ".." in rel_path.parts
    )


def _is_json_payload(path: str, media_type: str) -> bool:
    return path.endswith(".json") or media_type == "application/json"
