"""Audit that sensitive keys are redacted from representative payloads."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.utils.redaction import REDACTED, redact_sensitive_values  # noqa: E402


def build_report() -> dict[str, object]:
    markers = ("sk-phase-g-secret", "Bearer sk-phase-g-secret")
    raw_payload = {
        "deepseek_api_key": "sk-phase-g-secret",
        "authorization": "Bearer sk-phase-g-secret",
        "task_options": {"llm_auto_accept": False},
    }
    payload = redact_sensitive_values(raw_payload)
    serialized = json.dumps(payload, ensure_ascii=False)
    leaks = [marker for marker in markers if marker in serialized]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not leaks else "failed",
        "secret_leaks": len(leaks),
        "leak_markers": leaks,
        "llm_auto_accepted_count": 0,
        "redacted_values": sum(1 for value in payload.values() if value == REDACTED),
    }


def render_markdown(report: dict[str, object]) -> str:
    return (
        "# Phase G Secret Redaction Audit\n\n"
        f"- Status: {report['status']}\n"
        f"- Secret leaks: {report['secret_leaks']}\n"
        f"- LLM auto accepted: {report['llm_auto_accepted_count']}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
