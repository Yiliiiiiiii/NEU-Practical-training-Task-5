"""Build the strengthen-stage final gate report from evidence artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _status(condition: bool, *, partial: bool = False) -> str:
    if condition:
        return "pass"
    return "partial" if partial else "failed"


def _mapping_gate(splits: dict[str, Any]) -> tuple[str, list[str]]:
    notes: list[str] = []
    rows = [row for row in splits.get("splits", []) if isinstance(row, dict)]
    recall_ok = all(float(row.get("assisted_mapping_recall", 0.0)) >= 0.85 for row in rows)
    safety_ok = all(
        int(row.get("badcase_violations", 0)) == 0
        and int(row.get("required_missing", 0)) == 0
        and float(row.get("package_pass_rate", 0.0)) >= 1.0
        for row in rows
    )
    review_rate_ok = all(float(row.get("review_required_rate", 0.0)) <= 0.08 for row in rows)
    if not review_rate_ok:
        notes.append("mapping recall passed, but review_required_rate is above the 0.08 target in at least one split.")
    return _status(recall_ok and safety_ok, partial=not review_rate_ok), notes


def _package_gate(package: dict[str, Any]) -> str:
    return _status(
        float(package.get("package_verify_pass_rate", 0.0)) >= 1.0
        and float(package.get("checksum_pass_rate", 0.0)) >= 1.0
        and float(package.get("downstream_rag_jsonl_parse_pass", 0.0)) >= 1.0
    )


def _overfit_gate(overfit: dict[str, Any]) -> str:
    summary = overfit.get("summary", {})
    return _status(
        isinstance(summary, dict)
        and str(summary.get("decision", "")).lower() == "pass"
        and str(summary.get("risk_level", "")).lower() in {"low", "none"}
    )


def _llm_gate(llm: dict[str, Any]) -> str:
    if not llm:
        return "failed"
    if llm.get("llm_auto_accepted_count", 0) != 0:
        return "failed"
    if llm.get("unsafe_suggestion_count", 0) != 0 or llm.get("secret_leak_count", 0) != 0:
        return "partial"
    if llm.get("provider_configured") and llm.get("live_request_count", llm.get("llm_request_count", 0)) > 0:
        return "pass"
    if llm.get("can_claim_live_model_capability") is False:
        return "partial"
    return "partial"


def _review_gate(review: dict[str, Any]) -> str:
    if not review:
        return "failed"
    if review.get("unsafe_approve_count", 0) != 0:
        return "failed"
    if review.get("applied_count", 0) != 0 or review.get("production_write_count", 0) != 0:
        return "failed"
    if review.get("reviewed_items", 0) >= 20 and review.get("can_claim_live_subagent_review", False):
        return "pass"
    if review.get("reviewed_items", 0) >= 20:
        return "partial"
    return "failed"


def _content_gate(content: dict[str, Any]) -> str:
    tag = content.get("tag_metrics", {})
    summary = content.get("summary_metrics", {})
    if not isinstance(tag, dict) or not isinstance(summary, dict):
        return "failed"
    tag_ok = all(
        float(tag.get(key, 0.0)) >= 0.85
        for key in ("content_tag_f1", "management_tag_f1", "quality_tag_f1")
    )
    summary_ok = (
        float(summary.get("faithfulness_pass_rate", 0.0)) >= 0.95
        and int(summary.get("hallucination_count", 0)) == 0
    )
    return _status(tag_ok and summary_ok, partial=bool(tag or summary))


def _operation_gate(operation: dict[str, Any], schema: dict[str, Any]) -> str:
    return _status(
        float(operation.get("field_operation_accuracy", 0.0)) >= 0.95
        and int(operation.get("unsafe_operation_count", 0)) == 0
        and float(schema.get("localization_rate", 0.0)) >= 1.0
    )


def build_report(evidence_root: Path) -> dict[str, Any]:
    mapping = _load(evidence_root / "mapping" / "splits" / "summary.json")
    overfit = _load(evidence_root / "mapping" / "mapping_overfit_risk_report.json")
    llm = _load(evidence_root / "llm" / "deepseek_mapping_live_eval_report.json")
    review = _load(evidence_root / "review" / "codex_review_subagent_live_report.json")
    content = _load(evidence_root / "content" / "content_tag_summary_quality_report.json")
    package = _load(evidence_root / "package" / "package_consistency_report.json")
    operation = _load(evidence_root / "operation" / "field_operation_quality_report.json")
    schema = _load(evidence_root / "operation" / "schema_validation_localization_report.json")

    mapping_gate, notes = _mapping_gate(mapping)
    gates = {
        "mapping_gate": mapping_gate,
        "package_gate": _package_gate(package),
        "overfit_gate": _overfit_gate(overfit),
        "llm_gate": _llm_gate(llm),
        "review_subagent_gate": _review_gate(review),
        "content_quality_gate": _content_gate(content),
        "operation_schema_gate": _operation_gate(operation, schema),
        "doc_consistency_gate": "partial",
    }
    if any(value == "failed" for value in gates.values()):
        conclusion = "failed"
    elif any(value == "partial" for value in gates.values()):
        conclusion = "conditional_pass"
    else:
        conclusion = "pass"
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        **gates,
        "final_conclusion": conclusion,
        "notes": notes,
        "key_metrics": {
            "mapping_splits": mapping.get("splits", []),
            "llm_request_count": llm.get("live_request_count", llm.get("llm_request_count")),
            "reviewed_items": review.get("reviewed_items"),
            "content_tag_metrics": content.get("tag_metrics"),
            "summary_metrics": content.get("summary_metrics"),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    gates = [
        "mapping_gate",
        "package_gate",
        "overfit_gate",
        "llm_gate",
        "review_subagent_gate",
        "content_quality_gate",
        "operation_schema_gate",
        "doc_consistency_gate",
    ]
    lines = [
        "# Strengthen-stage Final Gate Result",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Final conclusion: {report['final_conclusion']}",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(f"| {gate} | {report[gate]} |" for gate in gates)
    if report.get("notes"):
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in report["notes"])
    lines.extend(["", "## Key Metrics", "", "```json"])
    lines.append(json.dumps(report["key_metrics"], ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.evidence_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_markdown(report), encoding="utf-8")
    args.out.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
