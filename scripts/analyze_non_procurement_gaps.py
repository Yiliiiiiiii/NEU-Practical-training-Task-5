"""Analyze non-procurement mapping gaps from exported package directories."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from eval_support import (
    load_jsonl,
    safe_ratio,
    score_mapping_report,
    write_json,
    write_markdown,
)
from package_consumption import resolved_package_dir

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_DOC_TYPES = ("general_doc", "meeting_doc", "policy_doc")
REQUIRED_TARGET_THRESHOLDS = {
    "general_doc": 2,
    "meeting_doc": 2,
    "policy_doc": 3,
}
MINIMUM_MAPPING_RECALL = 0.65
CORE_FILES = (
    "metadata.json",
    "mapping_report.json",
    "validation_report.json",
    "content.json",
    "canonical.json",
)
DEFAULT_PACKAGES_ROOT = ROOT / "reports" / "real_world_packages"
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_BADCASES = (
    ROOT / "examples" / "real_world" / "gold" / "real_world_badcases.jsonl"
)
DEFAULT_JSON = ROOT / "reports" / "non_procurement_gap_analysis.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "non_procurement_gap_analysis.md"

ACTION_BY_GAP = {
    "candidate_not_extracted": "enhance_candidate",
    "alias_missing": "add_alias",
    "regex_missing": "add_regex",
    "schema_too_strict": "review_schema",
    "transform_type_error": "enhance_transform",
    "badcase_sensitive": "keep_review_required",
}
DEFAULT_REASON_BY_GAP = {
    "candidate_not_extracted": "Expected source evidence produced no mapping candidate.",
    "alias_missing": "A source candidate exists but exact or alias mapping did not succeed.",
    "regex_missing": "Stable labeled source text lacks a deterministic mapping rule.",
    "schema_too_strict": "The required field has no gold or source evidence.",
    "transform_type_error": (
        "Candidate evidence exists but type normalization or validation failed."
    ),
    "badcase_sensitive": "The source/target pair is forbidden or was blocked by a badcase guard.",
}
TRANSFORM_MARKERS = (
    "transform",
    "type",
    "format",
    "normaliz",
    "parse",
    "invalid date",
    "expected a valid",
    "类型",
    "格式",
    "转换",
)
DATE_PATTERN = re.compile(
    r"(?:19|20)\d{2}(?:[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?)",
    re.IGNORECASE,
)
DOCUMENT_NUMBER_PATTERN = re.compile(
    r"(?:文号|编号|document\s*(?:number|no\.?))\s*[:：]?\s*[\w\u4e00-\u9fff-]+",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?:电话|手机|联系方式|phone|mobile|tel\.?)\s*[:：]?\s*(?:\+?\d[\d -]{5,}\d)",
    re.IGNORECASE,
)
NUMERIC_SUMMARY_FIELDS = {
    "accepted_count",
    "average_confidence",
    "avg_confidence",
    "badcase_blocked_count",
    "badcase_violation_count",
    "error_count",
    "failed_count",
    "llm_suggestion_count",
    "mapped_count",
    "mapped_fields",
    "mapping_recall",
    "required_missing_count",
    "required_unmapped_count",
    "review_required",
    "review_required_count",
    "target_fields",
    "total_candidates",
    "total_target_fields",
    "unmapped_required_fields",
    "warning_count",
}
GENERIC_TECHNICAL_METADATA_NAMES = {
    "content_hash",
    "dedupe_note",
    "extraction_version",
    "page_count",
    "page_text_lengths",
    "retrieved_at",
    "source_sha256",
    "source_site",
}


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Unable to read required JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Required JSON must contain an object: {path}")
    return payload


def _read_optional_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return _read_json_object(path)


def _read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        return load_jsonl(path)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSONL in {path}: {exc}") from exc


def discover_package_inventory(
    packages_root: Path,
) -> tuple[list[Path], dict[str, int]]:
    """Find complete package directories or ZIP exports with diagnostics."""
    if not packages_root.is_dir():
        raise ValueError(f"Package root not found or not a directory: {packages_root}")
    metadata_dirs = {metadata.parent for metadata in packages_root.rglob("metadata.json")}
    complete_dirs = {
        package
        for package in metadata_dirs
        if all((package / filename).is_file() for filename in CORE_FILES)
    }
    complete_zips: set[Path] = set()
    incomplete_zips = 0
    for zip_path in packages_root.rglob("*.zip"):
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = {
                    name.removeprefix("./")
                    for name in archive.namelist()
                    if name and not name.endswith("/")
                }
        except zipfile.BadZipFile:
            incomplete_zips += 1
            continue
        if all(filename in names for filename in CORE_FILES):
            complete_zips.add(zip_path)
        else:
            incomplete_zips += 1
    packages = sorted(complete_dirs | complete_zips, key=lambda path: path.as_posix())
    return packages, {
        "complete_packages_discovered": len(packages),
        "incomplete_package_count": len(metadata_dirs - complete_dirs) + incomplete_zips,
    }


def discover_package_dirs(packages_root: Path) -> list[Path]:
    """Find complete package directories at any depth."""
    packages, _ = discover_package_inventory(packages_root)
    return packages


def discover_packages(packages_root: Path) -> list[Path]:
    """Backward-compatible public name used by the implementation plan."""
    return discover_package_dirs(packages_root)


def parse_doc_types(value: str) -> tuple[str, ...]:
    requested = tuple(
        dict.fromkeys(item.strip() for item in value.split(",") if item.strip())
    )
    unsupported = sorted(set(requested) - set(SUPPORTED_DOC_TYPES))
    if unsupported:
        raise ValueError(
            "Unsupported --doc-types value(s): "
            f"{', '.join(unsupported)}; supported values are "
            f"{', '.join(SUPPORTED_DOC_TYPES)}"
        )
    if not requested:
        raise ValueError("--doc-types must select at least one supported document type")
    return requested


def _objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _first_string(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _nested_string(item: dict[str, Any], key: str, *nested_keys: str) -> str | None:
    value = item.get(key)
    return _first_string(value, *nested_keys) if isinstance(value, dict) else None


def _source_name(item: dict[str, Any]) -> str | None:
    return _first_string(item, "source_name", "source_field_name") or _nested_string(
        item, "source_field", "source_name", "name"
    )


def _source_path(item: dict[str, Any]) -> str | None:
    return _first_string(item, "source_path") or _nested_string(
        item, "source_field", "source_path", "path"
    )


def _target_field(item: dict[str, Any]) -> str | None:
    return _first_string(item, "target_field_id", "target_field", "field_id")


def _source_value(item: dict[str, Any]) -> str | None:
    for key in (
        "source_value",
        "value",
        "value_sample",
        "candidate_value",
        "raw_value",
    ):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    source_field = item.get("source_field")
    if isinstance(source_field, dict):
        return _source_value(source_field)
    return None


def _target_candidates(item: dict[str, Any]) -> set[str]:
    values = set(_strings(item.get("target_field_candidates")))
    target = _target_field(item)
    if target:
        values.add(target)
    return values


def _items(report: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    return [entry for key in keys for entry in _objects(report.get(key))]


def _missing_fields(validation: dict[str, Any], mapping: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for report in (validation, mapping):
        for key in (
            "required_missing",
            "missing_required_fields",
            "unmapped_required_fields",
        ):
            values.extend(_strings(report.get(key)))
    for item in _objects(mapping.get("unmapped")):
        target = _target_field(item)
        if target and item.get("required") is True:
            values.append(target)
    for issue in _items(validation, "issues", "errors", "validation_errors"):
        code = _first_string(issue, "code", "type") or ""
        target = _first_string(
            issue, "field_id", "field", "target_field_id", "target_field"
        )
        if target and "required" in code.casefold() and "missing" in code.casefold():
            values.append(target)
    return sorted(set(values))


def _validate_object_array(
    report_path: Path | str,
    report: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    if key not in report:
        return []
    value = report[key]
    path = f"{report_path}.{key}"
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list of objects")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}[{index}] must be an object")
    return value


def _validate_string_array(
    report_path: Path | str,
    report: dict[str, Any],
    key: str,
) -> list[str]:
    if key not in report:
        return []
    value = report[key]
    path = f"{report_path}.{key}"
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list of strings")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise ValueError(f"{path}[{index}] must be a non-empty string")
    return value


def _validate_optional_object(
    report_path: Path | str,
    report: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:
    if key not in report:
        return None
    value = report[key]
    path = f"{report_path}.{key}"
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _validate_mapping_entry(path: Path | str, item: dict[str, Any]) -> None:
    for key in ("target_field_candidates", "risk_flags", "source_blocks"):
        _validate_string_array(path, item, key)
    source_field = _validate_optional_object(path, item, "source_field")
    if source_field is not None:
        _validate_string_array(f"{path}.source_field", source_field, "source_blocks")
    _validate_optional_object(path, item, "badcase_filter")


def _validate_summary(report_path: Path, report: dict[str, Any]) -> None:
    if "summary" not in report:
        return
    summary = report["summary"]
    path = f"{report_path}.summary"
    if not isinstance(summary, dict):
        raise ValueError(f"{path} must be an object")
    for key in sorted(NUMERIC_SUMMARY_FIELDS & summary.keys()):
        value = summary[key]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{path}.{key} must be numeric")


def _validate_package_reports(
    package_dir: Path,
    mapping: dict[str, Any],
    validation: dict[str, Any],
    content: dict[str, Any],
    metadata: dict[str, Any],
    canonical: dict[str, Any],
) -> None:
    mapping_path = package_dir / "mapping_report.json"
    validation_path = package_dir / "validation_report.json"
    content_path = package_dir / "content.json"
    for key in (
        "mappings",
        "review_required_items",
        "review_evidence",
        "unmapped",
        "candidates",
        "mapping_candidates",
    ):
        entries = _validate_object_array(mapping_path, mapping, key)
        for index, item in enumerate(entries):
            _validate_mapping_entry(f"{mapping_path}.{key}[{index}]", item)
    for report_path, report in (
        (mapping_path, mapping),
        (validation_path, validation),
    ):
        for key in (
            "required_missing",
            "missing_required_fields",
            "unmapped_required_fields",
        ):
            _validate_string_array(report_path, report, key)
    for key in ("issues", "errors", "validation_errors"):
        _validate_object_array(validation_path, validation, key)
    if "passed" in validation and not isinstance(validation["passed"], bool):
        raise ValueError(f"{validation_path}.passed must be a boolean")
    _validate_summary(mapping_path, mapping)
    _validate_summary(validation_path, validation)
    blocks = _validate_object_array(content_path, content, "blocks")
    document = _validate_optional_object(content_path, content, "document")
    document_blocks: list[dict[str, Any]] = []
    if document is not None:
        document_blocks = _validate_object_array(
            f"{content_path}.document",
            document,
            "blocks",
        )
    for index, block in enumerate(blocks):
        _validate_optional_object(
            f"{content_path}.blocks[{index}]",
            block,
            "attributes",
        )
    for index, block in enumerate(document_blocks):
        _validate_optional_object(
            f"{content_path}.document.blocks[{index}]",
            block,
            "attributes",
        )
    _validate_optional_object(package_dir / "metadata.json", metadata, "metadata")
    _validate_optional_object(package_dir / "canonical.json", canonical, "metadata")


def _validate_reference_rows(
    gold_rows: list[dict[str, Any]],
    badcase_rows: list[dict[str, Any]],
) -> None:
    for index, row in enumerate(gold_rows):
        path = f"gold_rows[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{path} must be an object")
        for key in (
            "expected_mappings",
            "expected_review_required",
            "known_badcases",
        ):
            entries = _validate_object_array(path, row, key)
            for entry_index, entry in enumerate(entries):
                entry_path = f"{path}.{key}[{entry_index}]"
                if key == "known_badcases":
                    _validate_optional_object(
                        entry_path,
                        entry,
                        "forbidden_auto_mapping",
                    )
                else:
                    _validate_mapping_entry(entry_path, entry)
    for index, row in enumerate(badcase_rows):
        path = f"badcase_rows[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{path} must be an object")
        _validate_optional_object(path, row, "forbidden_auto_mapping")


def _load_package(package_dir: Path) -> dict[str, Any]:
    required = {
        filename.removesuffix(".json"): _read_json_object(package_dir / filename)
        for filename in CORE_FILES
    }
    required["content_organization_report"] = _read_optional_json_object(
        package_dir / "content_organization_report.json"
    )
    required["chunks"] = _read_optional_jsonl(package_dir / "chunks.jsonl")
    required["package_dir"] = package_dir
    _validate_package_reports(
        package_dir,
        required["mapping_report"],
        required["validation_report"],
        required["content"],
        required["metadata"],
        required["canonical"],
    )
    return required


def _package_identity(package: dict[str, Any]) -> tuple[str, str]:
    metadata = package["metadata"]
    canonical = package["canonical"]
    doc_id = (
        _first_string(metadata, "doc_id", "document_id")
        or _first_string(canonical, "doc_id", "document_id")
        or package["package_dir"].name
    )
    doc_type = (
        _first_string(metadata, "doc_type", "schema_id")
        or _nested_string(metadata, "metadata", "doc_type", "schema_id")
        or _first_string(canonical, "doc_type", "schema_id")
        or _nested_string(canonical, "metadata", "doc_type", "schema_id")
        or ""
    )
    return doc_id, doc_type


def _mapping_entries(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    return _items(
        mapping,
        "mappings",
        "review_required_items",
        "review_evidence",
        "unmapped",
        "candidates",
        "mapping_candidates",
    )


def _has_candidate_evidence(item: dict[str, Any]) -> bool:
    if _source_name(item) or _source_path(item) or _source_value(item):
        return True
    source = item.get("source_field")
    return isinstance(source, dict) and bool(source)


def _review_entries(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = _items(mapping, "review_required_items", "review_evidence")
    inferred = [
        item
        for item in _objects(mapping.get("mappings"))
        if item.get("status") == "review_required" or item.get("need_review") is True
    ]
    return explicit + inferred


def _accepted_entries(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in _objects(mapping.get("mappings"))
        if item.get("status", "accepted") == "accepted"
    ]


def _entry_matches_target(item: dict[str, Any], target: str) -> bool:
    return target in _target_candidates(item)


def _gold_item_is_accepted(
    accepted: list[dict[str, Any]],
    gold_item: dict[str, Any],
) -> bool:
    target = _target_field(gold_item)
    expected_name = _source_name(gold_item)
    expected_path = _source_path(gold_item)
    for actual in accepted:
        if _target_field(actual) != target:
            continue
        if expected_name:
            if _source_name(actual) == expected_name:
                return True
            continue
        if expected_path and _source_path(actual) == expected_path:
            return True
        if not expected_name and not expected_path:
            return True
    return False


def _content_blocks(package: dict[str, Any]) -> list[dict[str, Any]]:
    content = package["content"]
    blocks = _objects(content.get("blocks"))
    if blocks:
        return blocks
    document = content.get("document")
    return _objects(document.get("blocks")) if isinstance(document, dict) else []


def _block_text(block: dict[str, Any]) -> str:
    values: list[str] = []
    for key in ("text", "content", "value"):
        value = block.get(key)
        if isinstance(value, str) and value:
            values.append(value)
    attributes = block.get("attributes")
    if isinstance(attributes, dict):
        for value in attributes.values():
            if isinstance(value, str) and value:
                values.append(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        values.extend(
                            str(item)
                            for item in child.values()
                            if isinstance(item, str) and item
                        )
    return " ".join(values)


def _block_id(block: dict[str, Any]) -> str | None:
    return _first_string(block, "block_id", "id")


def _gold_source_samples(
    package: dict[str, Any],
    expected: list[dict[str, Any]],
    target: str,
) -> tuple[list[str], list[str]]:
    blocks = _content_blocks(package)
    samples: list[str] = []
    block_ids: list[str] = []
    for item in expected:
        if _target_field(item) != target:
            continue
        source_path = _source_path(item) or ""
        match = re.fullmatch(r"blocks\[(\d+)\](?:\..+)?", source_path)
        if match and int(match.group(1)) < len(blocks):
            block = blocks[int(match.group(1))]
            text = _block_text(block)
            if text:
                samples.append(text)
            if value := _block_id(block):
                block_ids.append(value)
    return samples, block_ids


def _is_stable_labeled_text(
    target: str,
    texts: Iterable[str],
    source_names: Iterable[str],
) -> bool:
    combined = "\n".join(texts)
    if not combined:
        return False
    lowered = combined.casefold()
    if "date" in target and DATE_PATTERN.search(combined):
        return any(
            marker in lowered
            for marker in ("date", "time", "日期", "时间", "发布", "签发", "会议")
        )
    if any(marker in target for marker in ("number", "code", "no")):
        return DOCUMENT_NUMBER_PATTERN.search(combined) is not None
    if any(marker in target for marker in ("phone", "mobile", "telephone")):
        return PHONE_PATTERN.search(combined) is not None
    for source_name in source_names:
        if source_name and source_name.casefold() in lowered:
            return (
                re.search(
                    rf"{re.escape(source_name)}\s*[:：]\s*\S+",
                    combined,
                    re.IGNORECASE,
                )
                is not None
            )
    return False


def _semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold().replace("_", " "))
        if len(token) > 1
    }


def _semantic_name_match(source_name: str | None, target: str) -> bool:
    if not source_name:
        return False
    source_tokens = _semantic_tokens(source_name)
    target_tokens = _semantic_tokens(target)
    return bool(target_tokens) and target_tokens <= source_tokens


def _item_matches_gold_evidence(
    item: dict[str, Any],
    expected: list[dict[str, Any]],
    target: str,
) -> bool:
    source_name = _source_name(item)
    source_path = _source_path(item)
    for gold_item in expected:
        if _target_field(gold_item) != target:
            continue
        expected_name = _source_name(gold_item)
        expected_path = _source_path(gold_item)
        if expected_name and source_name == expected_name:
            return True
        if expected_path and source_path == expected_path:
            return True
    return False


def _is_generic_metadata_evidence(
    item: dict[str, Any],
    expected: list[dict[str, Any]],
    target: str,
) -> bool:
    source_name = (_source_name(item) or "").casefold()
    source_path = (_source_path(item) or "").casefold()
    if not (
        source_path.startswith("$.metadata.")
        or source_path.startswith("metadata.")
    ):
        return False
    if (
        source_name in GENERIC_TECHNICAL_METADATA_NAMES
        and not _semantic_name_match(source_name, target)
    ):
        return True
    return not (
        _item_matches_gold_evidence(item, expected, target)
        or _semantic_name_match(source_name, target)
    )


def _has_target_specific_evidence(
    item: dict[str, Any],
    *,
    target: str,
    expected: list[dict[str, Any]],
) -> bool:
    if _is_generic_metadata_evidence(item, expected, target):
        return False
    if _item_matches_gold_evidence(item, expected, target):
        return True
    if _semantic_name_match(_source_name(item), target):
        return True
    source_blocks = _strings(item.get("source_blocks"))
    if not source_blocks and isinstance(item.get("source_field"), dict):
        source_blocks = _strings(item["source_field"].get("source_blocks"))
    if not source_blocks:
        return False
    source_value = _source_value(item)
    return _is_stable_labeled_text(
        target,
        [source_value] if source_value else [],
        [_source_name(item) or ""],
    )


def _validation_evidence(
    validation: dict[str, Any],
    target: str,
) -> list[dict[str, Any]]:
    issues = _items(validation, "issues", "errors", "validation_errors")
    result: list[dict[str, Any]] = []
    for issue in issues:
        issue_target = _first_string(
            issue, "field", "field_id", "target_field", "target_field_id"
        )
        if issue_target == target or target in str(issue.get("path", "")):
            result.append(issue)
    return result


def _reason_text(
    related: list[dict[str, Any]],
    validation_evidence: list[dict[str, Any]],
) -> str:
    values: list[str] = []
    for item in [*related, *validation_evidence]:
        for key in (
            "review_required_reason",
            "reason",
            "message",
            "error",
            "code",
        ):
            value = item.get(key)
            if isinstance(value, str) and value:
                values.append(value)
    return " ".join(dict.fromkeys(values))


def _forbidden_pairs(
    doc_id: str,
    gold: dict[str, Any],
    badcases: list[dict[str, Any]],
) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    all_cases = [
        *_objects(gold.get("known_badcases")),
        *(item for item in badcases if item.get("doc_id") == doc_id),
    ]
    for case in all_cases:
        forbidden = case.get("forbidden_auto_mapping")
        if not isinstance(forbidden, dict):
            source = _first_string(case, "source_name")
            target = _first_string(case, "forbidden_target_field")
            forbidden = (
                {"source_name": source, "target_field": target}
                if source and target
                else None
            )
        if isinstance(forbidden, dict):
            source = _source_name(forbidden)
            target = _target_field(forbidden)
            if source and target:
                pairs.add((source, target))
    return pairs


def _has_badcase_match(
    related: list[dict[str, Any]],
    target: str,
    forbidden_pairs: set[tuple[str, str]],
) -> bool:
    for item in related:
        badcase_filter = item.get("badcase_filter")
        if (
            item.get("status") == "badcase_blocked"
            or item.get("badcase_blocked") is True
            or "badcase_blocked" in _strings(item.get("risk_flags"))
            or (
                isinstance(badcase_filter, dict)
                and badcase_filter.get("blocked") is True
            )
            or (
                _source_name(item) is not None
                and (_source_name(item), target) in forbidden_pairs
            )
        ):
            return True
    return False


def _evidence_has_forbidden_pair(
    evidence: list[dict[str, Any]],
    target: str,
    forbidden_pairs: set[tuple[str, str]],
) -> bool:
    return any(
        (source_name, target) in forbidden_pairs
        for item in evidence
        if (source_name := _source_name(item))
    )


def _classification_evidence(item: dict[str, Any]) -> bool:
    if _has_candidate_evidence(item):
        return True
    flags = {flag.casefold() for flag in _strings(item.get("risk_flags"))}
    return bool(
        flags
        & {
            "badcase_blocked",
            "type_mismatch",
            "transform_error",
            "normalization_error",
        }
    )


def _classify_gap(
    *,
    target: str,
    related: list[dict[str, Any]],
    expected: list[dict[str, Any]],
    source_texts: list[str],
    validation_evidence: list[dict[str, Any]],
    forbidden_pairs: set[tuple[str, str]],
    required_missing: bool,
    ambiguous_gold: bool,
) -> str:
    reason = _reason_text(related, validation_evidence).casefold()
    if (
        ambiguous_gold
        or _has_badcase_match(related, target, forbidden_pairs)
        or _evidence_has_forbidden_pair(expected, target, forbidden_pairs)
    ):
        return "badcase_sensitive"
    risk_flags = " ".join(
        flag for item in related for flag in _strings(item.get("risk_flags"))
    ).casefold()
    if related and any(
        marker in f"{reason} {risk_flags}" for marker in TRANSFORM_MARKERS
    ):
        return "transform_type_error"
    source_names = [
        value
        for item in expected
        if _target_field(item) == target
        if (value := _source_name(item))
    ]
    if _is_stable_labeled_text(target, source_texts, source_names):
        return "regex_missing"
    if related:
        return "alias_missing"
    if any(_target_field(item) == target for item in expected):
        return "candidate_not_extracted"
    if required_missing:
        return "schema_too_strict"
    return "candidate_not_extracted"


def _gap_sort_key(item: dict[str, Any]) -> tuple[object, ...]:
    return (
        -int(item["count"]),
        str(item["doc_type"]),
        str(item["target_field"]),
        str(item["doc_id"]),
        str(item["gap_type"]),
    )


def _make_gap(
    *,
    doc_id: str,
    doc_type: str,
    target: str,
    gap_type: str,
    related: list[dict[str, Any]],
    source_texts: list[str],
    block_ids: list[str],
    validation_evidence: list[dict[str, Any]],
    recommendable: bool,
    is_missing: bool,
    is_review: bool,
) -> dict[str, Any]:
    source_names = sorted({value for item in related if (value := _source_name(item))})
    values = sorted(
        {value[:240] for item in related if (value := _source_value(item))}
        | {value[:240] for value in source_texts if value}
    )
    related_block_ids = [
        block_id
        for item in related
        for block_id in (
            _strings(item.get("source_blocks"))
            or _strings(
                item.get("source_field", {}).get("source_blocks")
                if isinstance(item.get("source_field"), dict)
                else None
            )
        )
    ]
    reason = _reason_text(related, validation_evidence)
    return {
        "doc_type": doc_type,
        "doc_id": doc_id,
        "target_field": target,
        "gap_type": gap_type,
        "count": 1,
        "candidate_source_names": source_names,
        "candidate_value_samples": values[:5],
        "source_block_ids": sorted(set([*block_ids, *related_block_ids]))[:10],
        "review_required_reason": reason or DEFAULT_REASON_BY_GAP[gap_type],
        "recommended_action": ACTION_BY_GAP[gap_type],
        "_recommendable": recommendable,
        "_is_missing": is_missing,
        "_is_review": is_review,
    }


def _summarize_gap_members(
    members: list[dict[str, Any]],
    *,
    include_variants: bool = False,
) -> dict[str, Any]:
    ordered = sorted(
        members,
        key=lambda item: (
            str(item["doc_id"]),
            str(item["gap_type"]),
            tuple(item["candidate_source_names"]),
            tuple(item["candidate_value_samples"]),
        ),
    )
    first = ordered[0]
    document_ids = sorted({str(item["doc_id"]) for item in ordered})
    reasons = sorted(
        {
            str(item["review_required_reason"])
            for item in ordered
            if item["review_required_reason"]
        }
    )
    result = {
        "doc_type": first["doc_type"],
        "doc_id": document_ids[0],
        "document_ids": document_ids[:10],
        "target_field": first["target_field"],
        "gap_type": first["gap_type"],
        "count": len(ordered),
        "candidate_source_names": sorted(
            {
                value
                for item in ordered
                for value in item["candidate_source_names"]
            }
        )[:10],
        "candidate_value_samples": sorted(
            {
                value
                for item in ordered
                for value in item["candidate_value_samples"]
            }
        )[:5],
        "source_block_ids": sorted(
            {value for item in ordered for value in item["source_block_ids"]}
        )[:10],
        "review_required_reason": (
            reasons[0] if reasons else DEFAULT_REASON_BY_GAP[first["gap_type"]]
        ),
        "recommended_action": first["recommended_action"],
    }
    if include_variants:
        result["gap_types"] = sorted({str(item["gap_type"]) for item in ordered})
        result["recommended_actions"] = sorted(
            {str(item["recommended_action"]) for item in ordered}
        )
    return result


def _aggregate_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for gap in gaps:
        key = (
            str(gap["doc_type"]),
            str(gap["target_field"]),
            str(gap["gap_type"]),
            str(gap["recommended_action"]),
        )
        grouped.setdefault(key, []).append(gap)

    result = [_summarize_gap_members(members) for members in grouped.values()]
    return sorted(result, key=_gap_sort_key)


def _aggregate_field_frequencies(
    gaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for gap in gaps:
        key = (str(gap["doc_type"]), str(gap["target_field"]))
        grouped.setdefault(key, []).append(gap)
    result = [
        _summarize_gap_members(members, include_variants=True)
        for members in grouped.values()
    ]
    return sorted(result, key=_gap_sort_key)


def _badcase_violation_count(
    gold: dict[str, Any],
    mapping: dict[str, Any],
    doc_badcases: list[dict[str, Any]],
) -> int:
    score_gold = dict(gold)
    score_gold["known_badcases"] = [
        *_objects(gold.get("known_badcases")),
        *doc_badcases,
    ]
    return int(score_mapping_report(score_gold, mapping)["badcase_violation_count"])


def analyze_packages(
    package_dirs: list[Path],
    gold_rows: list[dict[str, Any]],
    badcase_rows: list[dict[str, Any]],
    *,
    doc_types: tuple[str, ...] = SUPPORTED_DOC_TYPES,
    top_n: int,
    discovery_diagnostics: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Load, normalize, classify, and aggregate complete package directories."""
    if top_n < 1:
        raise ValueError("--top-n must be at least 1")
    unsupported = sorted(set(doc_types) - set(SUPPORTED_DOC_TYPES))
    if unsupported:
        raise ValueError(f"Unsupported document type(s): {', '.join(unsupported)}")

    _validate_reference_rows(gold_rows, badcase_rows)
    gold_by_doc = {
        str(row["doc_id"]): row
        for row in gold_rows
        if isinstance(row.get("doc_id"), str)
    }
    packages: list[tuple[str, str, dict[str, Any]]] = []
    ignored_doc_types: Counter[str] = Counter()
    for package_path in sorted(package_dirs, key=lambda path: path.as_posix()):
        with resolved_package_dir(package_path) as package_dir:
            package = _load_package(package_dir)
        package["package_dir"] = package_path
        doc_id, doc_type = _package_identity(package)
        if doc_type in doc_types:
            packages.append((doc_id, doc_type, package))
        else:
            ignored_doc_types[doc_type or "<missing>"] += 1
    packages.sort(
        key=lambda item: (item[1], item[0], item[2]["package_dir"].as_posix())
    )

    gaps: list[dict[str, Any]] = []
    metrics: dict[str, dict[str, Any]] = {
        doc_type: {
            "documents_total": 0,
            "strict_pass_count": 0,
            "review_required_count": 0,
            "required_missing_count": 0,
            "average_recall": 0.0,
            "badcase_violation_count": 0,
            "_recalls": [],
        }
        for doc_type in doc_types
    }

    for doc_id, doc_type, package in packages:
        mapping = package["mapping_report"]
        validation = package["validation_report"]
        gold = gold_by_doc.get(
            doc_id,
            {
                "doc_id": doc_id,
                "expected_mappings": [],
                "expected_review_required": [],
                "known_badcases": [],
            },
        )
        expected_mappings = _objects(gold.get("expected_mappings"))
        expected_reviews = _objects(gold.get("expected_review_required"))
        expected = [*expected_mappings, *expected_reviews]
        missing = _missing_fields(validation, mapping)
        reviews = _review_entries(mapping)
        accepted = _accepted_entries(mapping)
        entries = _mapping_entries(mapping)
        doc_badcases = [item for item in badcase_rows if item.get("doc_id") == doc_id]
        forbidden = _forbidden_pairs(doc_id, gold, badcase_rows)
        review_targets = {target for item in reviews if (target := _target_field(item))}
        unmatched_expected = [
            item for item in expected if not _gold_item_is_accepted(accepted, item)
        ]
        unmatched_gold_targets = {
            target
            for item in unmatched_expected
            if (target := _target_field(item))
        }
        badcase_targets = {
            target
            for item in entries
            if (target := _target_field(item))
            and _has_badcase_match([item], target, forbidden)
        }
        targets = sorted(
            set(missing) | review_targets | unmatched_gold_targets | badcase_targets
        )

        for target in targets:
            expected_for_target = [
                item for item in expected if _target_field(item) == target
            ]
            unmatched_for_target = [
                item for item in unmatched_expected if _target_field(item) == target
            ]
            safe_unmatched_for_target = [
                item for item in unmatched_for_target if item in expected_mappings
            ]
            ambiguous_gold = any(
                _target_field(item) == target for item in expected_reviews
            )
            related_candidates = [
                item
                for item in entries
                if _entry_matches_target(item, target)
                and _classification_evidence(item)
                and (
                    item in reviews
                    or item.get("status", "accepted") != "accepted"
                    or _has_badcase_match([item], target, forbidden)
                )
            ]
            related = [
                item
                for item in related_candidates
                if _has_badcase_match([item], target, forbidden)
                or _has_target_specific_evidence(
                    item,
                    target=target,
                    expected=expected_for_target,
                )
            ]
            display_gold = unmatched_for_target
            if not display_gold and (ambiguous_gold or target in badcase_targets):
                display_gold = expected_for_target
            source_texts, block_ids = _gold_source_samples(
                package,
                display_gold,
                target,
            )
            for item in related:
                if value := _source_value(item):
                    source_texts.append(value)
            validation_evidence = _validation_evidence(validation, target)
            gap_type = _classify_gap(
                target=target,
                related=related,
                expected=expected,
                source_texts=source_texts,
                validation_evidence=validation_evidence,
                forbidden_pairs=forbidden,
                required_missing=target in missing,
                ambiguous_gold=ambiguous_gold,
            )
            display_related = related or display_gold
            recommendable = (
                gap_type != "badcase_sensitive"
                and not ambiguous_gold
                and not any(
                    _is_generic_metadata_evidence(
                        item,
                        expected_for_target,
                        target,
                    )
                    for item in display_related
                )
                and bool(safe_unmatched_for_target or related)
            )
            gap = _make_gap(
                doc_id=doc_id,
                doc_type=doc_type,
                target=target,
                gap_type=gap_type,
                related=display_related,
                source_texts=source_texts,
                block_ids=block_ids,
                validation_evidence=validation_evidence,
                recommendable=recommendable,
                is_missing=target in missing,
                is_review=target in review_targets,
            )
            gaps.append(gap)

        score = score_mapping_report(gold, mapping)
        recall = float(score["mapping_recall"])
        badcase_violation_count = _badcase_violation_count(gold, mapping, doc_badcases)
        mapped_or_review_targets = {
            target
            for item in [*_accepted_entries(mapping), *reviews]
            if (target := _target_field(item))
        }
        strict_passed = (
            recall >= MINIMUM_MAPPING_RECALL
            and not missing
            and badcase_violation_count == 0
            and len(mapped_or_review_targets) >= REQUIRED_TARGET_THRESHOLDS[doc_type]
        )

        doc_metrics = metrics[doc_type]
        doc_metrics["documents_total"] += 1
        doc_metrics["strict_pass_count"] += int(strict_passed)
        doc_metrics["review_required_count"] += len(reviews)
        doc_metrics["required_missing_count"] += len(missing)
        doc_metrics["_recalls"].append(recall)
        doc_metrics["badcase_violation_count"] += badcase_violation_count

    for values in metrics.values():
        recalls = values.pop("_recalls")
        values["average_recall"] = safe_ratio(sum(recalls), len(recalls))
        values["documents"] = values["documents_total"]

    summary = {
        "documents_total": sum(item["documents_total"] for item in metrics.values()),
        "strict_pass_count": sum(
            item["strict_pass_count"] for item in metrics.values()
        ),
        "review_required_count": sum(
            item["review_required_count"] for item in metrics.values()
        ),
        "required_missing_count": sum(
            item["required_missing_count"] for item in metrics.values()
        ),
        "average_recall": safe_ratio(
            sum(
                item["average_recall"] * item["documents_total"]
                for item in metrics.values()
            ),
            sum(item["documents_total"] for item in metrics.values()),
        ),
        "badcase_violation_count": sum(
            item["badcase_violation_count"] for item in metrics.values()
        ),
        "by_doc_type": metrics,
        "diagnostics": {
            "complete_packages_discovered": (
                discovery_diagnostics or {}
            ).get("complete_packages_discovered", len(package_dirs)),
            "packages_analyzed": len(packages),
            "ignored_document_type_count": sum(ignored_doc_types.values()),
            "ignored_document_types": dict(sorted(ignored_doc_types.items())),
            "incomplete_package_count": (
                discovery_diagnostics or {}
            ).get("incomplete_package_count", 0),
        },
    }

    sorted_gaps = _aggregate_gaps(gaps)
    by_type = {
        "candidate_not_extracted": "candidate_extraction_gaps",
        "alias_missing": "alias_gaps",
        "regex_missing": "regex_gaps",
        "schema_too_strict": "schema_gaps",
        "transform_type_error": "transform_gaps",
        "badcase_sensitive": "badcase_sensitive_items",
    }
    report: dict[str, Any] = {
        "summary": summary,
        "top_missing_required_fields": _aggregate_field_frequencies(
            [item for item in gaps if item["_is_missing"]]
        )[:top_n],
        "top_review_required_fields": _aggregate_field_frequencies(
            [item for item in gaps if item["_is_review"]]
        )[:top_n],
    }
    for gap_type, key in by_type.items():
        report[key] = [item for item in sorted_gaps if item["gap_type"] == gap_type][
            :top_n
        ]
    report["recommended_plan"] = _aggregate_gaps(
        [item for item in gaps if item["_recommendable"]]
    )[:top_n]
    return report


def _markdown_cell(value: object) -> str:
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _append_gap_table(lines: list[str], items: list[dict[str, Any]]) -> None:
    if not items:
        lines.extend(["", "- None identified."])
        return
    lines.extend(
        [
            "",
            "| Document | Type | Target | Gap | Count | Sources | Reason | Action |",
            "|---|---|---|---|---:|---|---|---|",
        ]
    )
    for item in items:
        lines.append(
            "| {doc_id} | {doc_type} | {target} | {gap} | {count} | "
            "{sources} | {reason} | {action} |".format(
                doc_id=_markdown_cell(item["doc_id"]),
                doc_type=_markdown_cell(item["doc_type"]),
                target=_markdown_cell(item["target_field"]),
                gap=_markdown_cell(item["gap_type"]),
                count=item["count"],
                sources=_markdown_cell(item["candidate_source_names"]),
                reason=_markdown_cell(item["review_required_reason"]),
                action=_markdown_cell(item["recommended_action"]),
            )
        )


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Non-procurement Gap Analysis",
        "",
        "## Summary",
        "",
        "| Documents | Strict pass | Review required | Required missing | "
        "Average recall | Badcase violations |",
        "|---:|---:|---:|---:|---:|---:|",
        (
            f"| {summary['documents_total']} | {summary['strict_pass_count']} | "
            f"{summary['review_required_count']} | "
            f"{summary['required_missing_count']} | "
            f"{summary['average_recall']:.6f} | "
            f"{summary['badcase_violation_count']} |"
        ),
        "",
        "## By Document Type",
        "",
        "| Type | Documents | Strict pass | Review required | Required missing | "
        "Average recall | Badcase violations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for doc_type, values in summary["by_doc_type"].items():
        lines.append(
            f"| {doc_type} | {values['documents_total']} | "
            f"{values['strict_pass_count']} | {values['review_required_count']} | "
            f"{values['required_missing_count']} | "
            f"{values['average_recall']:.6f} | "
            f"{values['badcase_violation_count']} |"
        )

    sections = (
        ("Top Missing Required Fields", "top_missing_required_fields"),
        ("Top Review-required Fields", "top_review_required_fields"),
        ("Candidate Extraction Gaps", "candidate_extraction_gaps"),
        ("Alias Gaps", "alias_gaps"),
        ("Regex Rule Gaps", "regex_gaps"),
        ("Schema Required-field Gaps", "schema_gaps"),
        ("Transform / Type Normalization Gaps", "transform_gaps"),
        ("Badcase-sensitive Items", "badcase_sensitive_items"),
        ("Recommended Fix Plan", "recommended_plan"),
        ("Do-not-auto-accept List", "badcase_sensitive_items"),
    )
    for heading, key in sections:
        lines.extend(["", f"## {heading}"])
        _append_gap_table(lines, report[key])
    return "\n".join(lines).rstrip() + "\n"


def _load_jsonl_with_context(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Required JSONL input not found: {path}")
    try:
        return load_jsonl(path)
    except (json.JSONDecodeError, OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid JSONL in {path}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-root", type=Path, default=DEFAULT_PACKAGES_ROOT)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--badcases", type=Path, default=DEFAULT_BADCASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument(
        "--doc-types",
        default=",".join(SUPPORTED_DOC_TYPES),
        help="Comma-separated subset of general_doc,meeting_doc,policy_doc.",
    )
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()

    try:
        doc_types = parse_doc_types(args.doc_types)
        package_dirs, discovery_diagnostics = discover_package_inventory(
            args.packages_root
        )
        gold_rows = _load_jsonl_with_context(args.gold)
        badcase_rows = _load_jsonl_with_context(args.badcases)
        report = analyze_packages(
            package_dirs,
            gold_rows=gold_rows,
            badcase_rows=badcase_rows,
            doc_types=doc_types,
            top_n=args.top_n,
            discovery_diagnostics=discovery_diagnostics,
        )
    except ValueError as exc:
        parser.error(str(exc))
    write_json(args.out, report)
    write_markdown(args.markdown, render_markdown(report).splitlines())


if __name__ == "__main__":
    main()
