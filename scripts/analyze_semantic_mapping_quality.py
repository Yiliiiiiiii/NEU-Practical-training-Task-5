"""Analyze semantic mapping quality from exported SchemaPack packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase_c_report_metadata import attach_run_metadata  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGES_ROOT = ROOT / "reports" / "real_world_packages"
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_BADCASES = (
    ROOT / "examples" / "real_world" / "gold" / "real_world_badcases.jsonl"
)
DEFAULT_JSON = ROOT / "reports" / "semantic_mapping_quality_report.json"
DEFAULT_MD = ROOT / "reports" / "semantic_mapping_quality_report.md"

SUPPORTED_DOC_TYPES = {"general_doc", "meeting_doc", "policy_doc"}
REQUIRED_TARGET_THRESHOLDS = {
    "general_doc": 2,
    "meeting_doc": 2,
    "policy_doc": 3,
}
MINIMUM_MAPPING_RECALL = 0.65
FORBIDDEN_PAIRS = {
    ("成文日期", "publish_date"): "forbidden_issue_date_to_publish_date",
    ("发布日期", "effective_date"): "forbidden_publish_date_to_effective_date",
    ("retrieved_at", "effective_date"): "forbidden_retrieval_time_to_effective_date",
    ("主持人", "attendees"): "forbidden_chairperson_to_attendees",
    ("联系人", "attendees"): "forbidden_contact_to_attendees",
    ("联系人", "service_object"): "forbidden_contact_to_service_object",
    ("承办单位", "issuer"): "forbidden_organizer_to_issuer",
    ("解读机构", "issuer"): "forbidden_interpreter_to_issuer",
    ("预算金额", "award_amount"): "forbidden_budget_to_award",
    ("控制价", "award_amount"): "forbidden_control_price_to_award",
}
TRANSFORM_FAILURE_CODES = {
    "date_format_error",
    "date_format_invalid",
    "date_parse_failed",
    "date_type_error",
    "wrong_type",
    "array_item_invalid",
    "enum_invalid",
    "number_type_error",
}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain JSON objects")
        rows.append(value)
    return rows


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _source_name(item: dict[str, Any]) -> str:
    source = item.get("source_field")
    if isinstance(source, dict):
        value = source.get("source_name")
        if isinstance(value, str):
            return value
    for key in ("source_field_name", "source_name", "source_label"):
        value = item.get(key)
        if isinstance(value, str):
            return value
    return ""


def _target_field(item: dict[str, Any]) -> str:
    for key in ("target_field_id", "target_field", "field_id", "field"):
        value = item.get(key)
        if isinstance(value, str):
            return value
    return ""


def _normalized(value: str) -> str:
    return re.sub(r"[\s_:：\-./]+", "", value).lower()


def _source_matches(actual: str, expected: str) -> bool:
    left = _normalized(actual)
    right = _normalized(expected)
    return bool(left and right and (left == right or left.endswith(right) or right.endswith(left)))


def _entry_matches_gold(entry: dict[str, Any], gold: dict[str, Any]) -> bool:
    return _target_field(entry) == _target_field(gold) and _source_matches(
        _source_name(entry),
        _source_name(gold),
    )


def _read_json_bytes(value: bytes, name: str) -> dict[str, Any]:
    payload = json.loads(value.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return payload


def _load_package(path: Path) -> dict[str, dict[str, Any]]:
    names = (
        "metadata.json",
        "mapping_report.json",
        "validation_report.json",
        "transform_report.json",
    )
    if path.is_dir():
        return {
            name: json.loads((path / name).read_text(encoding="utf-8"))
            if (path / name).is_file()
            else {}
            for name in names
        }
    with ZipFile(path) as archive:
        members = {Path(name).name: name for name in archive.namelist()}
        return {
            name: _read_json_bytes(archive.read(members[name]), name)
            if name in members
            else {}
            for name in names
        }


def discover_packages(packages_root: str | Path) -> list[Path]:
    root = Path(packages_root)
    if root.is_file():
        return [root]
    archives = sorted(root.rglob("*.zip"))
    directories = sorted(
        path.parent
        for path in root.rglob("metadata.json")
        if (path.parent / "mapping_report.json").is_file()
        and not any(archive.parent == path.parent for archive in archives)
    )
    return [*archives, *directories]


def _badcase_pairs(
    doc_id: str,
    gold: dict[str, Any],
    badcases: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    pairs = dict(FORBIDDEN_PAIRS)
    rows = [
        *_objects(gold.get("known_badcases")),
        *(item for item in badcases if item.get("doc_id") in {None, doc_id}),
    ]
    for row in rows:
        forbidden = row.get("forbidden_auto_mapping")
        if isinstance(forbidden, dict):
            source = forbidden.get("source_name") or forbidden.get("source_field")
            target = forbidden.get("target_field") or forbidden.get("target_field_id")
            if isinstance(source, str) and isinstance(target, str):
                pairs[(source, target)] = str(
                    row.get("case_id") or row.get("badcase_type") or "badcase_forbidden"
                )
        source = row.get("source_field")
        targets = row.get("forbidden_target_fields")
        if isinstance(source, str) and isinstance(targets, list):
            for target in targets:
                if isinstance(target, str):
                    pairs[(source, target)] = str(
                        row.get("case_id") or "badcase_forbidden"
                    )
    return pairs


def _forbidden_reason(
    source_name: str,
    target_field: str,
    pairs: dict[tuple[str, str], str],
) -> str | None:
    for (source, target), reason in pairs.items():
        if target == target_field and _source_matches(source_name, source):
            return reason
    return None


def _validation_failures(validation: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for issue in _objects(validation.get("issues")):
        failure_type = issue.get("failure_type") or issue.get("code")
        if failure_type in TRANSFORM_FAILURE_CODES:
            failures.append(
                {
                    "target_field": _target_field(issue),
                    "failure_type": str(failure_type),
                    "message": str(issue.get("message") or ""),
                    "source_value": issue.get("source_value"),
                    "suggested_normalized_value": issue.get(
                        "suggested_normalized_value"
                    ),
                }
            )
    return failures


def _classify_missing_gap(
    gold_item: dict[str, Any],
    entries: list[dict[str, Any]],
    unmapped: list[dict[str, Any]],
) -> str:
    target = _target_field(gold_item)
    source = _source_name(gold_item)
    related = [
        item
        for item in entries
        if _target_field(item) == target or _source_matches(_source_name(item), source)
    ]
    reasons = " ".join(
        str(item.get("reason") or item.get("review_required_reason") or "")
        for item in unmapped
        if _target_field(item) == target
    ).lower()
    if "regex" in reasons:
        return "regex_missing"
    if any(_source_matches(_source_name(item), source) for item in related):
        if any(_target_field(item) != target for item in related):
            return "alias_missing"
        return "candidate_extracted_but_not_ranked"
    return "candidate_not_extracted"


def _recommended_action(gap_type: str) -> str:
    return {
        "candidate_not_extracted": "enhance_candidate_extraction",
        "candidate_extracted_but_not_ranked": "improve_evidence_ranking",
        "regex_missing": "add_regex_rule",
        "alias_missing": "add_safe_alias",
        "transform_invalid": "improve_transform_normalizer",
        "unsafe_ambiguous": "keep_review_or_block",
        "schema_requirement_mismatch": "review_schema_requirement",
        "gold_label_issue": "human_review_gold_label",
    }[gap_type]


def _risk(gap_type: str) -> str:
    if gap_type in {"unsafe_ambiguous", "gold_label_issue", "schema_requirement_mismatch"}:
        return "high"
    if gap_type in {"candidate_extracted_but_not_ranked", "transform_invalid"}:
        return "medium"
    return "low"


def analyze(
    *,
    packages_root: str | Path,
    gold_rows: list[dict[str, Any]],
    badcase_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_by_doc = {
        str(row["doc_id"]): row
        for row in gold_rows
        if isinstance(row.get("doc_id"), str)
    }
    gaps: list[dict[str, Any]] = []
    unsafe_candidates: list[dict[str, Any]] = []
    strict_failures: list[dict[str, Any]] = []
    recalls: list[float] = []
    strict_pass_count = 0
    review_required_count = 0
    required_missing_count = 0
    badcase_violations = 0
    llm_auto_accepted_count = 0
    documents: list[dict[str, Any]] = []

    for package_path in discover_packages(packages_root):
        package = _load_package(package_path)
        metadata = package["metadata.json"]
        mapping = package["mapping_report.json"]
        validation = package["validation_report.json"]
        doc_id = str(metadata.get("doc_id") or package_path.stem)
        gold = gold_by_doc.get(doc_id, {})
        doc_type = str(
            gold.get("doc_type")
            or metadata.get("schema_id")
            or mapping.get("schema_id")
            or "unknown"
        )
        accepted = _objects(mapping.get("mappings"))
        reviews = _objects(mapping.get("review_required_items"))
        unmapped = _objects(mapping.get("unmapped"))
        entries = [*accepted, *reviews]
        expected_mappings = _objects(gold.get("expected_mappings"))
        expected_reviews = _objects(gold.get("expected_review_required"))
        expected = [*expected_mappings, *expected_reviews]
        pairs = _badcase_pairs(doc_id, gold, badcase_rows)
        doc_violations = 0

        for item in accepted:
            source = _source_name(item)
            target = _target_field(item)
            forbidden = _forbidden_reason(source, target, pairs)
            if forbidden is not None:
                doc_violations += 1
                unsafe_candidates.append(
                    {
                        "doc_id": doc_id,
                        "doc_type": doc_type,
                        "source_name": source,
                        "target_field": target,
                        "reason": forbidden,
                        "source_path": item.get("source_path")
                        or (item.get("source_field") or {}).get("source_path"),
                    }
                )
                gaps.append(
                    {
                        "doc_id": doc_id,
                        "doc_type": doc_type,
                        "target_field": target,
                        "source_name": source,
                        "gap_type": "unsafe_ambiguous",
                        "recommended_action": _recommended_action("unsafe_ambiguous"),
                        "risk": _risk("unsafe_ambiguous"),
                    }
                )
            if str(item.get("method") or item.get("strategy")) == "llm_fallback":
                llm_auto_accepted_count += 1

        matched = 0
        for gold_item in expected_mappings:
            if any(_entry_matches_gold(entry, gold_item) for entry in accepted):
                matched += 1
                continue
            target = _target_field(gold_item)
            gap_type = _classify_missing_gap(gold_item, entries, unmapped)
            gaps.append(
                {
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "target_field": target,
                    "source_name": _source_name(gold_item),
                    "gap_type": gap_type,
                    "recommended_action": _recommended_action(gap_type),
                    "risk": _risk(gap_type),
                }
            )
        for gold_item in expected_reviews:
            if any(_entry_matches_gold(entry, gold_item) for entry in reviews):
                matched += 1
                continue
            source = _source_name(gold_item)
            target = _target_field(gold_item)
            if _forbidden_reason(source, target, pairs) is not None and any(
                _entry_matches_gold(entry, gold_item) for entry in accepted
            ):
                continue
            gap_type = _classify_missing_gap(gold_item, entries, unmapped)
            gaps.append(
                {
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "target_field": target,
                    "source_name": source,
                    "gap_type": gap_type,
                    "recommended_action": _recommended_action(gap_type),
                    "risk": _risk(gap_type),
                }
            )

        failures = _validation_failures(validation)
        for failure in failures:
            strict_failures.append({"doc_id": doc_id, "doc_type": doc_type, **failure})
            gaps.append(
                {
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "target_field": failure["target_field"],
                    "source_name": "",
                    "gap_type": "transform_invalid",
                    "recommended_action": _recommended_action("transform_invalid"),
                    "risk": _risk("transform_invalid"),
                }
            )

        expected_targets = {_target_field(item) for item in expected}
        for item in unmapped:
            target = _target_field(item)
            if item.get("required"):
                required_missing_count += 1
                if target not in expected_targets:
                    gaps.append(
                        {
                            "doc_id": doc_id,
                            "doc_type": doc_type,
                            "target_field": target,
                            "source_name": "",
                            "gap_type": "schema_requirement_mismatch",
                            "recommended_action": _recommended_action(
                                "schema_requirement_mismatch"
                            ),
                            "risk": _risk("schema_requirement_mismatch"),
                        }
                    )

        total_expected = len(expected)
        recall = matched / total_expected if total_expected else 1.0
        recalls.append(recall)
        review_required_count += len(reviews)
        badcase_violations += doc_violations
        mapped_targets = {
            _target_field(item) for item in entries if _target_field(item)
        }
        strict_passed = (
            doc_type in SUPPORTED_DOC_TYPES
            and recall >= MINIMUM_MAPPING_RECALL
            and not any(item.get("required") for item in unmapped)
            and doc_violations == 0
            and len(mapped_targets) >= REQUIRED_TARGET_THRESHOLDS[doc_type]
        )
        strict_pass_count += int(strict_passed)
        documents.append(
            {
                "doc_id": doc_id,
                "doc_type": doc_type,
                "mapping_recall": recall,
                "strict_passed": strict_passed,
                "review_required_count": len(reviews),
                "badcase_violations": doc_violations,
            }
        )

    by_doc_type = Counter(str(item["doc_type"]) for item in gaps)
    by_target_field = Counter(str(item["target_field"]) for item in gaps)
    by_gap_type = Counter(str(item["gap_type"]) for item in gaps)
    ranked_counts = Counter(
        (
            str(item["doc_type"]),
            str(item["target_field"]),
            str(item["gap_type"]),
            str(item["recommended_action"]),
            str(item["risk"]),
        )
        for item in gaps
        if item["gap_type"]
        not in {"unsafe_ambiguous", "schema_requirement_mismatch", "gold_label_issue"}
    )
    ranked_fixes = [
        {
            "rank": rank,
            "doc_type": key[0],
            "target_field": key[1],
            "gap_type": key[2],
            "count": count,
            "recommended_action": key[3],
            "risk": key[4],
            "expected_gain": f"reduce {key[1]} {key[2]} gaps",
        }
        for rank, (key, count) in enumerate(
            sorted(
                ranked_counts.items(),
                key=lambda item: (-item[1], item[0][0], item[0][1], item[0][2]),
            ),
            start=1,
        )
    ]
    dataset_size = len(documents)
    return {
        "summary": {
            "dataset_size": dataset_size,
            "average_recall": sum(recalls) / len(recalls) if recalls else 0.0,
            "strict_pass_count": strict_pass_count,
            "strict_total": dataset_size,
            "review_required_count": review_required_count,
            "required_missing_count": required_missing_count,
            "badcase_violations": badcase_violations,
            "llm_auto_accepted_count": llm_auto_accepted_count,
        },
        "gaps_by_doc_type": dict(sorted(by_doc_type.items())),
        "gaps_by_target_field": dict(sorted(by_target_field.items())),
        "gaps_by_gap_type": dict(sorted(by_gap_type.items())),
        "ranked_fixes": ranked_fixes,
        "unsafe_candidates": sorted(
            unsafe_candidates,
            key=lambda item: (
                item["doc_type"],
                item["doc_id"],
                item["target_field"],
                item["source_name"],
            ),
        ),
        "strict_validation_failures": sorted(
            strict_failures,
            key=lambda item: (
                item["doc_type"],
                item["doc_id"],
                item["target_field"],
            ),
        ),
        "gold_label_suspicions": [],
        "documents": documents,
    }


def _table(lines: list[str], rows: list[tuple[object, ...]]) -> None:
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Semantic Mapping Quality Report",
        "",
        "## 总体指标",
        "",
        "| 指标 | 值 |",
        "| --- | ---: |",
    ]
    _table(lines, [(key, value) for key, value in summary.items()])
    lines.extend(
        [
            "",
            "## 按文档类型",
            "",
            "| doc_type | gap_count |",
            "| --- | ---: |",
        ]
    )
    _table(lines, list(report["gaps_by_doc_type"].items()))
    lines.extend(
        [
            "",
            "## 按目标字段",
            "",
            "| target_field | gap_count |",
            "| --- | ---: |",
        ]
    )
    _table(lines, list(report["gaps_by_target_field"].items()))
    lines.extend(
        [
            "",
            "## Ranked Fixes",
            "",
            "| rank | doc_type | target_field | gap_type | count | action | risk |",
            "| ---: | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    _table(
        lines,
        [
            (
                item["rank"],
                item["doc_type"],
                item["target_field"],
                item["gap_type"],
                item["count"],
                item["recommended_action"],
                item["risk"],
            )
            for item in report["ranked_fixes"]
        ],
    )
    lines.extend(["", "## Unsafe Candidates", ""])
    if report["unsafe_candidates"]:
        for item in report["unsafe_candidates"]:
            lines.append(
                f"- {item['doc_id']}: {item['source_name']} -> "
                f"{item['target_field']} ({item['reason']})"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Strict Validation Failures", ""])
    if report["strict_validation_failures"]:
        for item in report["strict_validation_failures"]:
            lines.append(
                f"- {item['doc_id']}.{item['target_field']}: "
                f"{item['failure_type']} — {item['message']}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## 禁止自动修复项",
            "",
            "- Forbidden pairs, medium/low-confidence fuzzy mappings, LLM-only "
            "suggestions, and source-untraceable mappings must not be auto accepted.",
            "",
            "## 下一步建议",
            "",
        ]
    )
    if report["ranked_fixes"]:
        for item in report["ranked_fixes"][:10]:
            lines.append(
                f"- {item['doc_type']}.{item['target_field']}: "
                f"{item['recommended_action']} ({item['count']})"
            )
    else:
        lines.append("- No safe automatic fix is currently ranked.")
    return "\n".join(lines) + "\n"


def run(
    *,
    packages_root: str | Path,
    gold_path: str | Path,
    badcases_path: str | Path,
    out_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    report = analyze(
        packages_root=packages_root,
        gold_rows=load_jsonl(gold_path),
        badcase_rows=load_jsonl(badcases_path),
    )
    attach_run_metadata(
        report,
        packages_root=packages_root,
        gold_path=gold_path,
        badcases_path=badcases_path,
    )
    if out_path is not None:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if markdown_path is not None:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-root", type=Path, default=DEFAULT_PACKAGES_ROOT)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--badcases", type=Path, default=DEFAULT_BADCASES)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        packages_root=args.packages_root,
        gold_path=args.gold,
        badcases_path=args.badcases,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
