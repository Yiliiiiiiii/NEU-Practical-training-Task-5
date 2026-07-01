"""Evaluate safe LLM fallback modes without requiring network credentials."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings  # noqa: E402
from app.schemas.mapping import FieldCandidate  # noqa: E402
from app.schemas.target_schema import TargetField  # noqa: E402
from app.services.llm_fallback_service import (  # noqa: E402
    LLMFallbackRequest,
    LLMFallbackService,
    LLMFallbackSuggestion,
    hash_text,
)

REPORT_JSON = "llm_fallback_eval_report.json"
REPORT_MD = "llm_fallback_eval_report.md"


class CountingAdapter:
    enabled = True
    model = "counting-test-adapter"

    def __init__(self) -> None:
        self.call_count = 0

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        self.call_count += 1
        return LLMFallbackSuggestion(
            candidate=request.candidates[0] if request.candidates else None,
            confidence=0.5,
            reason="Counting adapter suggestion requires review.",
            model=self.model,
            latency_ms=0,
            prompt_hash=hash_text(request.task_id),
            response_hash=hash_text("counting"),
        )


class ErrorAdapter:
    enabled = True
    model = "error-test-adapter"

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        return LLMFallbackSuggestion(
            candidate=request.candidates[0] if request.candidates else None,
            confidence=0.5,
            reason="Synthetic provider failure.",
            model=self.model,
            latency_ms=7,
            prompt_hash=hash_text(request.task_id),
            response_hash=hash_text("provider_error"),
            error_code="request_failed",
        )


def sample_field() -> TargetField:
    return TargetField(
        field_id="buyer_name",
        name="buyer_name",
        display_name="采购人",
        type="string",
        required=False,
        aliases=[],
    )


def sample_candidates() -> list[FieldCandidate]:
    return [
        FieldCandidate(
            candidate_id="cand_buyer",
            task_id="task_llm_eval",
            doc_id="doc_llm_eval",
            source_path="metadata.采购方名称",
            source_name="采购方名称",
            value_sample="国家广播电视总局监管中心",
            inferred_type="string",
            source_blocks=["b1"],
            confidence=0.25,
            evidence=["low-confidence source candidate"],
        )
    ]


def settings_for_mode(
    mode: str,
    *,
    allow_network: bool = False,
    secret: str | None = None,
) -> Settings:
    if mode == "disabled":
        return Settings(llm_mode="disabled", llm_fallback_enabled=False, _env_file=None)
    if mode == "stub":
        kwargs = {"llm_api_key": secret} if secret is not None else {}
        return Settings(
            llm_mode="mock",
            llm_fallback_enabled=True,
            _env_file=None,
            **kwargs,
        )
    if mode == "openai-compatible":
        if not allow_network:
            raise ValueError("openai-compatible mode requires --allow-network")
        kwargs = {"llm_api_key": secret} if secret is not None else {}
        return Settings(
            llm_mode="openai_compatible",
            llm_fallback_enabled=True,
            _env_file=None,
            **kwargs,
        )
    raise ValueError(f"unsupported mode: {mode}")


def _result_from_mapping(
    *,
    mode: str,
    settings: Settings,
    mapping: Any,
    started_at: str,
) -> dict[str, Any]:
    suggestion_count = 1 if mapping is not None else 0
    review_required_count = 1 if mapping is not None and mapping.need_review else 0
    auto_accepted_count = (
        1 if mapping is not None and mapping.status == "accepted" else 0
    )
    provider_error_count = (
        1
        if mapping is not None and (mapping.llm_metadata or {}).get("error_code")
        else 0
    )
    result = {
        "mode": mode,
        "started_at": started_at,
        "suggestion_count": suggestion_count,
        "review_required_count": review_required_count,
        "auto_accepted_count": auto_accepted_count,
        "badcase_blocked_count": 0,
        "provider_error_count": provider_error_count,
        "timeout_count": 0,
        "latency_ms": (mapping.llm_metadata or {}).get("latency_ms", 0)
        if mapping
        else 0,
        "secret_redaction_passed": True,
        "safe_config": LLMFallbackService(settings).safe_config_snapshot(),
        "mapping": mapping.model_dump(mode="json") if mapping else None,
    }
    result["secret_redaction_passed"] = "sk-test-secret-value" not in json.dumps(result)
    return result


def evaluate_mode(
    mode: str,
    *,
    root: Path = ROOT,
    secret: str | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    del root
    settings = settings_for_mode(mode, allow_network=allow_network, secret=secret)
    service = LLMFallbackService(settings)
    started_at = datetime.now(UTC).isoformat()
    mapping = service.suggest_mapping(
        task_id="task_llm_eval",
        field=sample_field(),
        candidates=sample_candidates(),
        used_source_paths=set(),
        badcases=[],
        strict_failure=False,
    )
    return _result_from_mapping(
        mode=mode,
        settings=settings,
        mapping=mapping,
        started_at=started_at,
    )


def evaluate_provider_error(*, root: Path = ROOT, strict: bool) -> dict[str, Any]:
    del root
    settings = Settings(llm_mode="mock", llm_fallback_enabled=True, _env_file=None)
    service = LLMFallbackService(settings, adapter=ErrorAdapter())
    raised = False
    mapping = None
    try:
        mapping = service.suggest_mapping(
            task_id=f"task_provider_error_{strict}",
            field=sample_field(),
            candidates=sample_candidates(),
            used_source_paths=set(),
            badcases=[],
            strict_failure=strict,
        )
    except RuntimeError:
        raised = True
    result = _result_from_mapping(
        mode=f"provider-error-{'strict' if strict else 'non-strict'}",
        settings=settings,
        mapping=mapping,
        started_at=datetime.now(UTC).isoformat(),
    )
    result["provider_error_count"] = 1
    result["raised"] = raised
    return result


def evaluate_badcase_block(*, root: Path = ROOT) -> dict[str, Any]:
    del root
    adapter = CountingAdapter()
    settings = Settings(llm_mode="mock", llm_fallback_enabled=True, _env_file=None)
    service = LLMFallbackService(settings, adapter=adapter)
    mapping = service.suggest_mapping(
        task_id="task_badcase_block",
        field=sample_field(),
        candidates=sample_candidates(),
        used_source_paths=set(),
        badcases=[
            {
                "source_field": "采购方名称",
                "forbidden_target_fields": ["buyer_name"],
            }
        ],
        strict_failure=False,
    )
    return {
        "mode": "badcase-block",
        "suggestion_count": 0 if mapping is None else 1,
        "review_required_count": 0,
        "auto_accepted_count": 0,
        "badcase_blocked_count": 1 if mapping is None else 0,
        "provider_call_count": adapter.call_count,
        "secret_redaction_passed": True,
        "safe_config": service.safe_config_snapshot(),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        "suggestion_count": sum(
            int(item.get("suggestion_count", 0)) for item in results
        ),
        "review_required_count": sum(
            int(item.get("review_required_count", 0)) for item in results
        ),
        "auto_accepted_count": sum(
            int(item.get("auto_accepted_count", 0)) for item in results
        ),
        "badcase_blocked_count": sum(
            int(item.get("badcase_blocked_count", 0)) for item in results
        ),
        "provider_error_count": sum(
            int(item.get("provider_error_count", 0)) for item in results
        ),
        "timeout_count": sum(int(item.get("timeout_count", 0)) for item in results),
        "latency_ms": sum(int(item.get("latency_ms", 0)) for item in results),
        "secret_redaction_passed": all(
            bool(item.get("secret_redaction_passed", False)) for item in results
        ),
    }
    if metrics["auto_accepted_count"] != 0:
        raise AssertionError("LLM suggestions must never be auto-accepted")
    if not metrics["secret_redaction_passed"]:
        raise AssertionError("secret redaction failed")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "metrics": metrics,
        "mode_results": results,
        "network_mode": "not_run",
        "boundaries": [
            "Disabled and stub modes do not require credentials.",
            "OpenAI-compatible mode is rejected unless --allow-network is supplied.",
            "LLM suggestions remain review-required and are never auto-accepted.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# LLM Fallback Evaluation Report",
        "",
        f"- Status: {report['status']}",
        f"- Suggestions: {metrics['suggestion_count']}",
        f"- Review required: {metrics['review_required_count']}",
        f"- Auto accepted: {metrics['auto_accepted_count']}",
        f"- Badcase blocked: {metrics['badcase_blocked_count']}",
        f"- Provider errors: {metrics['provider_error_count']}",
        f"- Secret redaction passed: {str(metrics['secret_redaction_passed']).lower()}",
        "",
        "## Modes",
        "",
        "| Mode | Suggestions | Review | Auto accepted | Provider errors |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in report["mode_results"]:
        lines.append(
            "| {mode} | {suggestions} | {review} | {accepted} | {errors} |".format(
                mode=item["mode"],
                suggestions=item.get("suggestion_count", 0),
                review=item.get("review_required_count", 0),
                accepted=item.get("auto_accepted_count", 0),
                errors=item.get("provider_error_count", 0),
            )
        )
    return "\n".join(lines) + "\n"


def write_reports(output_dir: Path, report: dict[str, Any]) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REPORT_JSON
    markdown_path = output_dir / REPORT_MD
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def run_evaluation(output_dir: Path = ROOT / "reports") -> dict[str, Any]:
    results = [
        evaluate_mode("disabled"),
        evaluate_mode("stub", secret="sk-test-secret-value"),
        evaluate_provider_error(strict=False),
        evaluate_provider_error(strict=True),
        evaluate_badcase_block(),
    ]
    report = aggregate(results)
    write_reports(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--mode", choices=["all", "disabled", "stub"], default="all")
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    if args.mode == "all":
        report = run_evaluation(args.output_dir)
    else:
        result = evaluate_mode(args.mode, allow_network=args.allow_network)
        report = aggregate([result])
        write_reports(args.output_dir, report)
    print(report["metrics"])


if __name__ == "__main__":
    main()
