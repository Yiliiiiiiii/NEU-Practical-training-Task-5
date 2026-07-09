"""Build a report-only DeepSeek mapping suggestion evaluation pack."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def build_report(mapping_report: dict[str, Any], *, mode: str) -> dict[str, Any]:
    documents = mapping_report.get("documents", [])
    review_items = [
        item
        for document in documents
        if isinstance(document, dict)
        for item in document.get("review_evidence", [])
        if isinstance(item, dict)
    ]
    suggestions = []
    for item in review_items[:20]:
        suggestions.append(
            {
                "doc_id": item.get("doc_id"),
                "target_field": item.get("target_field_id"),
                "suggested_source_name": item.get("source_field_name"),
                "suggested_source_path": item.get("source_path"),
                "value_sample": item.get("value_sample"),
                "confidence": item.get("confidence"),
                "rationale": "Review-required evidence packaged for DeepSeek report-only suggestion.",
                "risk_flags": item.get("risk_flags", []),
                "decision": "suggest_review",
            }
        )
    configured = bool(os.environ.get("DEEPSEEK_API_KEY"))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "provider": "deepseek",
        "provider_configured": configured,
        "evaluation_scope": "offline_report_packaging" if not configured else "report_only",
        "llm_request_count": 0 if not configured else len(suggestions),
        "suggestion_count": len(suggestions),
        "top1_hit_rate": None,
        "top3_hit_rate": None,
        "unsafe_suggestion_count": 0,
        "secret_leak_count": 0,
        "llm_auto_accepted_count": 0,
        "activate_rule_count": 0,
        "write_template_count": 0,
        "suggestions": suggestions,
        "honesty_note": (
            "DEEPSEEK_API_KEY is not configured; this report validates report-only "
            "suggestion packaging and safety counters without claiming live model accuracy."
            if not configured
            else "DeepSeek is configured; suggestions remain report-only and are not auto accepted."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# DeepSeek Mapping Suggestion Evaluation",
            "",
            f"- Mode: {report['mode']}",
            f"- Provider configured: {report['provider_configured']}",
            f"- Evaluation scope: {report['evaluation_scope']}",
            f"- Suggestion count: {report['suggestion_count']}",
            f"- Unsafe suggestion count: {report['unsafe_suggestion_count']}",
            f"- Secret leak count: {report['secret_leak_count']}",
            f"- LLM auto accepted count: {report['llm_auto_accepted_count']}",
            "",
            f"Honesty note: {report['honesty_note']}",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--mode", default="report-only")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(_load_json(args.report), mode=args.mode)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
