"""Apply explicit human review decisions to a Phase C evidence pack report."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "reports" / "review_evidence_pack.json"
DEFAULT_DECISIONS = ROOT / "reports" / "review_manual_decisions.jsonl"
DEFAULT_JSON = ROOT / "reports" / "review_manual_apply_report.json"
DEFAULT_MD = ROOT / "reports" / "review_manual_apply_report.md"
VALID_DECISIONS = {"approve", "reject", "keep_pending"}


def _read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_decisions(path: str | Path) -> dict[str, dict[str, Any]]:
    decision_path = Path(path)
    if not decision_path.exists():
        return {}
    decisions: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(decision_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{decision_path}:{line_number} must be a JSON object")
        review_id = payload.get("review_id")
        decision = payload.get("decision")
        if not isinstance(review_id, str) or not review_id:
            raise ValueError(f"{decision_path}:{line_number} missing review_id")
        if decision not in VALID_DECISIONS:
            raise ValueError(f"{decision_path}:{line_number} invalid decision: {decision!r}")
        decisions[review_id] = payload
    return decisions


def apply_decisions(evidence_pack: dict[str, Any], decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    reviews = evidence_pack.get("reviews", [])
    reviews = [item for item in reviews if isinstance(item, dict)]
    known_ids = {str(item.get("review_id")) for item in reviews}
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for review in reviews:
        review_id = str(review.get("review_id") or "")
        decision = decisions.get(review_id)
        if decision is None:
            skipped.append(
                {
                    "review_id": review_id,
                    "status": "skipped",
                    "reason": "no_manual_decision",
                }
            )
            continue
        action = str(decision["decision"])
        operator = decision.get("operator")
        warnings: list[str] = []
        if action == "approve" and operator != "human":
            skipped.append(
                {
                    "review_id": review_id,
                    "status": "skipped",
                    "decision": action,
                    "reason": "approve_requires_human_operator",
                }
            )
            continue
        flags = [flag for flag in review.get("risk_flags", []) if isinstance(flag, str)]
        if action == "approve" and flags:
            warnings.append("approved_review_has_risk_flags")
        if action == "approve" and review.get("codex_suggestion") != "approve":
            warnings.append("manual_approve_overrides_non_approve_suggestion")
        applied.append(
            {
                "review_id": review_id,
                "status": "applied",
                "decision": action,
                "operator": operator,
                "target_field": review.get("target_field"),
                "doc_id": review.get("doc_id"),
                "warnings": warnings,
                "external_mutation": False,
            }
        )

    unknown = sorted(set(decisions) - known_ids)
    for review_id in unknown:
        skipped.append(
            {
                "review_id": review_id,
                "status": "skipped",
                "reason": "unknown_review_id",
            }
        )

    counts = Counter(item.get("decision") for item in applied)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "evidence_review_count": len(reviews),
            "manual_decision_count": len(decisions),
            "applied_count": len(applied),
            "skipped_count": len(skipped),
            "applied_approve": counts.get("approve", 0),
            "applied_reject": counts.get("reject", 0),
            "applied_keep_pending": counts.get("keep_pending", 0),
            "external_mutations": 0,
        },
        "applied": applied,
        "skipped": skipped,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Phase C Manual Review Apply Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Evidence reviews: {summary['evidence_review_count']}",
        f"- Manual decisions: {summary['manual_decision_count']}",
        f"- Applied: {summary['applied_count']}",
        f"- Skipped: {summary['skipped_count']}",
        f"- External mutations: {summary['external_mutations']}",
        "",
        "## Applied",
        "",
    ]
    if report["applied"]:
        for item in report["applied"]:
            lines.append(f"- {item['review_id']}: {item['decision']} ({item['doc_id']} / {item['target_field']})")
    else:
        lines.append("- None")
    lines.extend(["", "## Skipped", ""])
    if report["skipped"]:
        for item in report["skipped"]:
            lines.append(f"- {item['review_id']}: {item['reason']}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def run(
    *,
    evidence_path: str | Path,
    decisions_path: str | Path,
    out_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    report = apply_decisions(_read_json(evidence_path), load_decisions(decisions_path))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = Path(markdown_path)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(
        evidence_path=args.evidence,
        decisions_path=args.decisions,
        out_path=args.out,
        markdown_path=args.markdown,
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
