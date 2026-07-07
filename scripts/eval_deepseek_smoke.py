from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.services.external_uir_llm_service import (  # noqa: E402
    ExternalUIRLLMSuggestionService,
)


def run_smoke() -> dict[str, Any]:
    settings = Settings(external_uir_llm_enabled=True, _env_file=None)
    payload = {
        "title": "测试公告",
        "sections": [
            {"heading": "发布日期", "text": "2026-02-02"},
            {"heading": "正文", "text": "本公告用于 DeepSeek JSON smoke。"},
        ],
    }
    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": settings.external_uir_llm_provider,
        "model": settings.deepseek_model,
        "base_url": settings.deepseek_base_url,
        "status": "failed",
        "suggestion_count": 0,
        "warning_count": 0,
        "must_not_auto_accept_mapping": True,
        "must_not_activate_catalog": True,
        "secret_leak_detected": False,
    }
    try:
        report = ExternalUIRLLMSuggestionService(settings).suggest_adapter_mappings(
            payload_excerpt=payload,
            unknown_paths=["payload.sections[0].heading", "payload.sections[0].text"],
            dialect_hint="deepseek_smoke",
            source_system="phase_d_smoke",
        )
    except Exception as exc:
        summary["error_type"] = type(exc).__name__
        summary["error"] = _safe_error(str(exc))
        return summary

    dumped = report.model_dump(mode="json")
    serialized = json.dumps(dumped, ensure_ascii=False).lower()
    summary.update(
        {
            "status": "passed",
            "suggestion_count": len(report.suggestions),
            "warning_count": len(report.warnings),
            "must_not_auto_accept_mapping": report.must_not_auto_accept_mapping,
            "must_not_activate_catalog": report.must_not_activate_catalog,
            "secret_leak_detected": "sk-" in serialized
            or "authorization" in serialized
            or "bearer " in serialized,
        }
    )
    return summary


def _safe_error(message: str) -> str:
    lowered = message.lower()
    if "authorization" in lowered or "bearer " in lowered or "sk-" in lowered:
        return "redacted"
    return message[:300]


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# DeepSeek Smoke Report",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in report.items():
        lines.append(f"| {key} | {str(value).replace('|', '\\|')} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "deepseek_smoke_report.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports" / "deepseek_smoke_report.md")
    args = parser.parse_args()

    report = run_smoke()
    write_json(args.out, report)
    write_markdown(args.markdown, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "passed" and not report["secret_leak_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
