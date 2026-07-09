"""Rank mapping gaps by document type, target field, and estimated gain."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "examples" / "real_world" / "gold" / "mapping_gold.jsonl"
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_JSON = ROOT / "reports" / "mapping_gap_analysis.json"
DEFAULT_MD = ROOT / "reports" / "mapping_gap_analysis.md"

REQUIRED_WEIGHT = 3
RECALL_WEIGHT = 1
BADCASE_RISK_PENALTY = 2


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _target_names(items: Any) -> set[str]:
    targets: set[str] = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                target = item.get("target_field") or item.get("target_field_id")
                if isinstance(target, str) and target:
                    targets.add(target)
    return targets


def _review_reason_counts(review_items: Any) -> Counter[str]:
    counts: Counter[str] = Counter()
    if isinstance(review_items, list):
        for item in review_items:
            if not isinstance(item, dict):
                continue
            reason = item.get("review_required_reason") or item.get("reason")
            counts[str(reason or "review_required")] += 1
    return counts


def build_gap_analysis(
    *,
    gold_rows: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    gold_by_doc = {str(row.get("doc_id")): row for row in gold_rows}
    documents = report.get("documents") or report.get("per_document") or []
    if not isinstance(documents, list):
        documents = []

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    reason_counts: Counter[str] = Counter()
    doc_type_counts: Counter[str] = Counter()
    for item in documents:
        if not isinstance(item, dict):
            continue
        doc_id = str(item.get("doc_id"))
        doc_type = str(item.get("doc_type", "unknown"))
        doc_type_counts[doc_type] += 1
        gold = gold_by_doc.get(doc_id, {})
        expected_targets = _target_names(gold.get("expected_mappings"))
        mapped_or_review = {
            target for target in item.get("mapped_or_review_targets", []) if isinstance(target, str)
        }
        missing_required = {
            target for target in item.get("required_missing", []) if isinstance(target, str)
        }
        missing_targets = (expected_targets - mapped_or_review) | missing_required
        review_counts = _review_reason_counts(item.get("review_evidence"))
        reason_counts.update(review_counts)
        badcase_targets = _target_names(
            [
                badcase.get("forbidden_auto_mapping")
                for badcase in gold.get("known_badcases", [])
                if isinstance(badcase, dict)
            ]
        )
        for target in sorted(missing_targets):
            key = (doc_type, target)
            entry = grouped.setdefault(
                key,
                {
                    "doc_type": doc_type,
                    "field": target,
                    "missing_count": 0,
                    "required_missing_count": 0,
                    "review_required_count": 0,
                    "badcase_risk_count": 0,
                    "document_ids": [],
                    "failure_reasons": Counter(),
                },
            )
            entry["missing_count"] += 1
            entry["required_missing_count"] += 1 if target in missing_required else 0
            entry["badcase_risk_count"] += 1 if target in badcase_targets else 0
            entry["document_ids"].append(doc_id)
            for reason in item.get("failure_reasons", []):
                entry["failure_reasons"][str(reason)] += 1
        for target in mapped_or_review & expected_targets:
            key = (doc_type, target)
            entry = grouped.setdefault(
                key,
                {
                    "doc_type": doc_type,
                    "field": target,
                    "missing_count": 0,
                    "required_missing_count": 0,
                    "review_required_count": 0,
                    "badcase_risk_count": 0,
                    "document_ids": [],
                    "failure_reasons": Counter(),
                },
            )
            entry["review_required_count"] += sum(review_counts.values())

    candidates = []
    for entry in grouped.values():
        estimated_gain = (
            entry["required_missing_count"] * REQUIRED_WEIGHT
            + entry["missing_count"] * RECALL_WEIGHT
            - entry["badcase_risk_count"] * BADCASE_RISK_PENALTY
        )
        candidates.append(
            {
                **{key: value for key, value in entry.items() if key != "failure_reasons"},
                "estimated_gain": estimated_gain,
                "failure_reasons": dict(entry["failure_reasons"]),
                "risk": "high" if entry["badcase_risk_count"] else "medium",
            }
        )
    candidates.sort(
        key=lambda item: (
            -int(item["estimated_gain"]),
            str(item["doc_type"]),
            str(item["field"]),
        )
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_report": str(DEFAULT_REPORT),
        "weights": {
            "required_weight": REQUIRED_WEIGHT,
            "recall_weight": RECALL_WEIGHT,
            "badcase_risk_penalty": BADCASE_RISK_PENALTY,
        },
        "by_doc_type": dict(doc_type_counts),
        "review_required_reasons": dict(reason_counts),
        "ranked_improvement_candidates": candidates,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Mapping Gap Analysis",
        "",
        "## Ranked Improvement Candidates",
        "",
        "| Rank | Doc Type | Field | Missing | Required Missing | Review Required | Estimated Gain | Risk |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for index, item in enumerate(report["ranked_improvement_candidates"][:30], start=1):
        lines.append(
            f"| {index} | {item['doc_type']} | {item['field']} | "
            f"{item['missing_count']} | {item['required_missing_count']} | "
            f"{item['review_required_count']} | {item['estimated_gain']} | {item['risk']} |"
        )
    lines.extend(["", "## Review-required Reasons", ""])
    if report["review_required_reasons"]:
        for reason, count in sorted(report["review_required_reasons"].items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    report = build_gap_analysis(gold_rows=_load_jsonl(args.gold), report=_load_json(args.report))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
