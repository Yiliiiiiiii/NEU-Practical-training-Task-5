"""Generate a Codex review subagent dry-run report from mapping review items."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _decision(item: dict[str, Any]) -> str:
    flags = {str(flag) for flag in item.get("risk_flags", [])}
    confidence = float(item.get("confidence") or 0.0)
    if "badcase_blocked" in flags or "high_risk" in flags:
        return "reject"
    if confidence >= 0.9 and not flags:
        return "approve"
    return "uncertain"


def build_report(mapping_report: dict[str, Any], *, mode: str) -> dict[str, Any]:
    documents = mapping_report.get("documents", [])
    decisions = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        for item in document.get("review_evidence", []):
            if not isinstance(item, dict):
                continue
            decision = _decision(item)
            decisions.append(
                {
                    "doc_id": document.get("doc_id"),
                    "target_field": item.get("target_field_id"),
                    "source_name": item.get("source_field_name"),
                    "source_path": item.get("source_path"),
                    "decision": decision,
                    "confidence": item.get("confidence"),
                    "risk_flags": item.get("risk_flags", []),
                    "reason": "Dry-run human-like review; no production rule is written.",
                }
            )
    counts = Counter(item["decision"] for item in decisions)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "reviewed_items": len(decisions),
        "approve_count": counts["approve"],
        "reject_count": counts["reject"],
        "uncertain_count": counts["uncertain"],
        "unsafe_approve_count": 0,
        "applied_count": 0,
        "production_write_count": 0,
        "decisions": decisions,
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Codex Review Subagent Dry-run",
            "",
            f"- Mode: {report['mode']}",
            f"- Reviewed items: {report['reviewed_items']}",
            f"- Approve: {report['approve_count']}",
            f"- Reject: {report['reject_count']}",
            f"- Uncertain: {report['uncertain_count']}",
            f"- Unsafe approve count: {report['unsafe_approve_count']}",
            f"- Applied count: {report['applied_count']}",
            "",
            "Dry-run only: no active knowledge pack or production rule was changed.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--mode", default="dry-run")
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
