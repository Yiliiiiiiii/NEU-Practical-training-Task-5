"""Preview scoped knowledge-pack impact without activation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

BLOCKED_REASON = (
    "Knowledge pack impact preview was not run because no apply-guarded "
    "approvals were produced for the current Phase G scope."
)


def build_report(args: argparse.Namespace) -> dict[str, object]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "blocked",
        "pack_scope": args.pack_scope,
        "dataset": str(args.dataset),
        "activated": False,
        "badcase_violations": 0,
        "review_required_delta": 0,
        "global_unintended_impact": False,
        "reason": BLOCKED_REASON,
    }


def render_markdown(report: dict[str, object]) -> str:
    return (
        "# Phase G Knowledge Pack Impact Preview\n\n"
        f"- Status: {report['status']}\n"
        f"- Activated: {report['activated']}\n"
        f"- Badcase violations: {report['badcase_violations']}\n"
        f"- Reason: {report['reason']}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pack-scope", default="phase_g")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
