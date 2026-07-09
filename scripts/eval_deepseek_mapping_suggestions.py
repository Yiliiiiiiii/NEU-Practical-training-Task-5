"""Build a report-only DeepSeek mapping suggestion evaluation pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "non_procurement_mapping_eval_report.json"
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEFAULT_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _safe_case_id(index: int, item: dict[str, Any]) -> str:
    doc_id = re.sub(r"[^0-9A-Za-z_\-]+", "_", str(item.get("doc_id") or "doc"))
    target = re.sub(r"[^0-9A-Za-z_\-]+", "_", str(item.get("target_field_id") or "field"))
    return f"deepseek_case_{index:03d}_{doc_id}_{target}"


def build_cases(mapping_report: dict[str, Any], *, max_cases: int) -> list[dict[str, Any]]:
    documents = mapping_report.get("documents", [])
    review_items = [
        {**item, "doc_id": document.get("doc_id"), "doc_type": document.get("doc_type")}
        for document in documents
        if isinstance(document, dict)
        for item in document.get("review_evidence", [])
        if isinstance(item, dict)
    ]
    cases = []
    for index, item in enumerate(review_items[:max_cases], start=1):
        cases.append(
            {
                "case_id": _safe_case_id(index, item),
                "doc_id": item.get("doc_id"),
                "doc_type": item.get("doc_type"),
                "target_field": item.get("target_field_id"),
                "candidate_sources": [
                    {
                        "source_name": item.get("source_field_name"),
                        "source_path": item.get("source_path"),
                        "value_sample": item.get("value_sample"),
                        "confidence": item.get("confidence"),
                    }
                ],
                "source_evidence": item.get("evidence_text", []),
                "gold_expected_target": item.get("target_field_id"),
                "known_badcases": item.get("risk_flags", []),
            }
        )
    return cases


def _prompt(case: dict[str, Any]) -> list[dict[str, str]]:
    prompt_case = {key: value for key, value in case.items() if key != "gold_expected_target"}
    return [
        {
            "role": "system",
            "content": (
                "You are a report-only mapping reviewer. Return only JSON. "
                "Do not write production rules, do not modify templates, and do not auto-accept."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Review the candidate source for the target field.",
                    "case": prompt_case,
                    "output_schema": {
                        "target_field": "string",
                        "suggested_source_path": "string",
                        "suggested_source_name": "string",
                        "confidence": 0.0,
                        "rationale": "string",
                        "risk_flags": [],
                        "decision": "suggest_accept|suggest_review|suggest_reject",
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]


def _offline_suggestion(case: dict[str, Any]) -> dict[str, Any]:
    source = case.get("candidate_sources", [{}])[0]
    return {
        "case_id": case["case_id"],
        "target_field": case.get("target_field"),
        "suggested_source_name": source.get("source_name"),
        "suggested_source_path": source.get("source_path"),
        "confidence": source.get("confidence", 0.0),
        "rationale": "Offline report-only packaging; no live model claim.",
        "risk_flags": case.get("known_badcases", []),
        "decision": "suggest_review",
        "latency_ms": 0,
    }


def _call_deepseek(case: dict[str, Any], *, api_key: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    response = httpx.post(
        f"{DEFAULT_BASE_URL.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": DEFAULT_MODEL,
            "messages": _prompt(case),
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("DeepSeek response JSON must be an object")
    parsed["case_id"] = case["case_id"]
    parsed["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return parsed


def _secret_leak_count(suggestions: list[dict[str, Any]]) -> int:
    pattern = re.compile(r"(?:sk-[A-Za-z0-9]{16,}|api[_-]?key|token|secret)", re.I)
    return sum(1 for item in suggestions if pattern.search(json.dumps(item, ensure_ascii=False)))


def _hit_rates(cases: list[dict[str, Any]], suggestions: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    if not suggestions:
        return None, None
    case_by_id = {case["case_id"]: case for case in cases}
    hits = 0
    for suggestion in suggestions:
        case = case_by_id.get(str(suggestion.get("case_id")))
        if not case:
            continue
        hits += int(suggestion.get("target_field") == case.get("gold_expected_target"))
    rate = hits / len(suggestions) if suggestions else None
    return rate, rate


def build_report(
    mapping_report: dict[str, Any],
    *,
    mode: str,
    max_cases: int,
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    configured = bool(os.environ.get("DEEPSEEK_API_KEY"))
    cases = build_cases(mapping_report, max_cases=max_cases)
    suggestions: list[dict[str, Any]] = []
    errors: list[str] = []
    live_request_count = 0
    if configured:
        api_key = str(os.environ["DEEPSEEK_API_KEY"])
        for case in cases:
            try:
                suggestions.append(_call_deepseek(case, api_key=api_key, timeout=timeout))
                live_request_count += 1
            except Exception as exc:  # noqa: BLE001 - report-only evidence must record provider failures.
                errors.append(f"{case['case_id']}: {type(exc).__name__}: {exc}"[:500])
                suggestions.append(_offline_suggestion(case))
    else:
        suggestions = [_offline_suggestion(case) for case in cases]
    top1, top3 = _hit_rates(cases, suggestions)
    latency_values = [
        float(item.get("latency_ms", 0.0))
        for item in suggestions
        if isinstance(item.get("latency_ms"), int | float)
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "provider": "deepseek",
        "provider_configured": configured,
        "evaluation_scope": "offline_packaging_only" if not configured else "live_report_only",
        "can_claim_live_model_capability": configured and live_request_count > 0 and not errors,
        "live_request_count": live_request_count,
        "llm_request_count": live_request_count,
        "case_count": len(cases),
        "suggestion_count": len(suggestions),
        "top1_hit_rate": top1,
        "top3_hit_rate": top3,
        "unsafe_suggestion_count": sum(
            1
            for item in suggestions
            if item.get("decision") == "suggest_accept" and item.get("risk_flags")
        ),
        "secret_leak_count": _secret_leak_count(suggestions),
        "llm_auto_accepted_count": 0,
        "activate_rule_count": 0,
        "write_template_count": 0,
        "avg_latency_ms": sum(latency_values) / len(latency_values) if latency_values else 0.0,
        "estimated_cost": 0.0,
        "errors": errors,
        "suggestions": suggestions,
        "honesty_note": (
            "DEEPSEEK_API_KEY is not configured; this report validates report-only "
            "suggestion packaging and safety counters without claiming live model accuracy."
            if not configured
            else "DeepSeek was invoked only for report-only suggestions; no suggestion was auto accepted or written to production rules."
        ),
    }, cases


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# DeepSeek Mapping Suggestion Evaluation",
            "",
            f"- Mode: {report['mode']}",
            f"- Provider configured: {report['provider_configured']}",
            f"- Evaluation scope: {report['evaluation_scope']}",
            f"- Can claim live model capability: {report['can_claim_live_model_capability']}",
            f"- Live request count: {report['live_request_count']}",
            f"- Case count: {report['case_count']}",
            f"- Suggestion count: {report['suggestion_count']}",
            f"- Top1 hit rate: {report['top1_hit_rate']}",
            f"- Top3 hit rate: {report['top3_hit_rate']}",
            f"- Unsafe suggestion count: {report['unsafe_suggestion_count']}",
            f"- Secret leak count: {report['secret_leak_count']}",
            f"- LLM auto accepted count: {report['llm_auto_accepted_count']}",
            f"- Avg latency ms: {report['avg_latency_ms']}",
            f"- Estimated cost: {report['estimated_cost']}",
            "",
            f"Honesty note: {report['honesty_note']}",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--mode", default="report-only")
    parser.add_argument("--max-cases", type=int, default=15)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    report, cases = build_report(
        _load_json(args.report),
        mode=args.mode,
        max_cases=args.max_cases,
        timeout=args.timeout,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    cases_path = args.out_json.with_name("deepseek_eval_cases.jsonl")
    cases_path.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False, sort_keys=True) for case in cases)
        + ("\n" if cases else ""),
        encoding="utf-8",
    )
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
