"""Build machine-readable Phase H semantic mapping gap drilldown."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "reports" / "phase_g_semantic_mapping_quality_report.json"
DEFAULT_JSON = ROOT / "reports" / "phase_h_mapping_gap_drilldown.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "phase_h_mapping_gap_drilldown.md"

ACTION_BY_GAP = {
    "candidate_not_extracted": "enhance_candidate_extraction",
    "candidate_extracted_but_not_ranked": "improve_evidence_ranking",
    "candidate_ranked_but_review_required": "review_semantic_risk",
    "candidate_ranked_but_badcase_blocked": "keep_review_required",
    "value_normalization_failed": "improve_value_normalizer",
    "date_format_invalid": "improve_date_normalizer",
    "missing_required": "enhance_required_field_extraction",
    "schema_route_low_confidence": "improve_schema_route_evidence",
    "source_not_present": "needs_human_source_review",
    "transform_invalid": "improve_value_normalizer",
    "schema_requirement_mismatch": "review_schema_requirement",
    "unsafe_ambiguous": "keep_review_or_block",
}
RISK_BY_GAP = {
    "candidate_not_extracted": "low",
    "candidate_extracted_but_not_ranked": "medium",
    "candidate_ranked_but_review_required": "medium",
    "candidate_ranked_but_badcase_blocked": "high",
    "value_normalization_failed": "medium",
    "date_format_invalid": "medium",
    "missing_required": "medium",
    "schema_route_low_confidence": "medium",
    "source_not_present": "high",
    "transform_invalid": "medium",
    "schema_requirement_mismatch": "high",
    "unsafe_ambiguous": "high",
}
DATE_FIELDS = {
    "publish_date",
    "effective_date",
    "valid_until",
    "meeting_date",
    "deadline",
    "created_date",
}


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _objects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _shape_for_field(target_field: str) -> str:
    if target_field in DATE_FIELDS or target_field.endswith("_date"):
        return "date"
    if target_field in {"attendees", "topics", "action_items", "decisions"}:
        return "array_or_text"
    return "unknown"


def _notes(document: dict[str, Any]) -> str:
    recall = document.get("mapping_recall")
    recall_text = f"{float(recall):.4f}" if isinstance(recall, int | float) else "unknown"
    return (
        f"mapping_recall={recall_text}; "
        f"strict_passed={document.get('strict_passed')}; "
        f"review_required_count={document.get('review_required_count', 0)}"
    )


def _rank_lookup(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for fix in _objects(report.get("ranked_fixes")):
        doc_type = str(fix.get("doc_type") or "unknown")
        grouped.setdefault(doc_type, []).append(fix)
    for fixes in grouped.values():
        fixes.sort(key=lambda item: int(item.get("rank") or 9999))
    return grouped


def _item_from_document(document: dict[str, Any], fix: dict[str, Any]) -> dict[str, Any]:
    target = str(fix.get("target_field") or "unknown")
    gap_type = str(fix.get("gap_type") or "candidate_not_extracted")
    return {
        "doc_id": str(document.get("doc_id") or "unknown"),
        "doc_type": str(document.get("doc_type") or fix.get("doc_type") or "unknown"),
        "target_field": target,
        "gap_type": gap_type,
        "gold_value_shape": _shape_for_field(target),
        "current_decision": None,
        "candidate_present": gap_type != "candidate_not_extracted",
        "source_anchor_present": gap_type not in {"candidate_not_extracted", "source_not_present"},
        "risk": str(fix.get("risk") or RISK_BY_GAP.get(gap_type, "medium")),
        "recommended_action": str(
            fix.get("recommended_action") or ACTION_BY_GAP.get(gap_type, "inspect_gap")
        ),
        "notes": _notes(document),
    }


def build_drilldown(report: dict[str, Any], *, top_n: int = 30) -> dict[str, Any]:
    ranked_fixes = _objects(report.get("ranked_fixes"))[:top_n]
    ranked_by_doc_type = _rank_lookup(report)
    documents = _objects(report.get("documents"))
    items: list[dict[str, Any]] = []
    for document in documents:
        doc_type = str(document.get("doc_type") or "unknown")
        fixes = ranked_by_doc_type.get(doc_type) or ranked_fixes[:1]
        if not fixes:
            continue
        for fix in fixes[:1]:
            items.append(_item_from_document(document, fix))
    if not items:
        for fix in ranked_fixes:
            count = int(fix.get("count") or 1)
            for index in range(max(1, min(count, top_n - len(items)))):
                items.append(
                    _item_from_document(
                        {
                            "doc_id": f"aggregate_{index + 1}",
                            "doc_type": fix.get("doc_type"),
                            "mapping_recall": None,
                            "strict_passed": None,
                            "review_required_count": 0,
                        },
                        fix,
                    )
                )
                if len(items) >= top_n:
                    break
            if len(items) >= top_n:
                break
    items = sorted(items, key=lambda item: (item["doc_type"], item["doc_id"], item["target_field"]))[:top_n]
    by_doc_type = Counter(item["doc_type"] for item in items)
    by_target_field = Counter(item["target_field"] for item in items)
    by_gap_type = Counter(item["gap_type"] for item in items)
    source_by_doc_type = report.get("gaps_by_doc_type") if isinstance(report.get("gaps_by_doc_type"), dict) else None
    source_by_target = report.get("gaps_by_target_field") if isinstance(report.get("gaps_by_target_field"), dict) else None
    source_by_gap = report.get("gaps_by_gap_type") if isinstance(report.get("gaps_by_gap_type"), dict) else None
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "dataset_size": (report.get("summary") or {}).get("dataset_size", len(documents))
            if isinstance(report.get("summary"), dict)
            else len(documents),
            "gap_count": sum(int(value) for value in (source_by_gap or by_gap_type).values()),
            "by_doc_type": dict(sorted((source_by_doc_type or by_doc_type).items())),
            "by_target_field": dict(sorted((source_by_target or by_target_field).items())),
            "by_gap_type": dict(sorted((source_by_gap or by_gap_type).items())),
            "top_ranked_fixes": ranked_fixes,
        },
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase H Mapping Gap Drilldown",
        "",
        f"- Dataset size: {report['summary']['dataset_size']}",
        f"- Gap count: {report['summary']['gap_count']}",
        "",
        "## Top Ranked Fixes",
        "",
    ]
    fixes = report["summary"].get("top_ranked_fixes") or []
    if fixes:
        for fix in fixes[:30]:
            lines.append(
                f"- {fix.get('doc_type')}.{fix.get('target_field')}: "
                f"{fix.get('gap_type')} x{fix.get('count')} -> "
                f"{fix.get('recommended_action')} ({fix.get('risk')})"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Items",
            "",
            "| Doc | Type.Field | Gap | Candidate present | Source anchor | Risk | Action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["items"][:30]:
        lines.append(
            f"| {item['doc_id']} | {item['doc_type']}.{item['target_field']} | "
            f"{item['gap_type']} | {item['candidate_present']} | "
            f"{item['source_anchor_present']} | {item['risk']} | "
            f"{item['recommended_action']} |"
        )
    return "\n".join(lines) + "\n"


def run(
    *,
    source_report: str | Path,
    out_path: str | Path,
    markdown_path: str | Path,
    top_n: int = 30,
) -> dict[str, Any]:
    report = build_drilldown(read_json(source_report), top_n=top_n)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reports-root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--top-n", type=int, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.source_report
    if args.reports_root is not None and source == DEFAULT_SOURCE:
        source = args.reports_root / DEFAULT_SOURCE.name
    report = run(
        source_report=source,
        out_path=args.out,
        markdown_path=args.markdown,
        top_n=args.top_n,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
