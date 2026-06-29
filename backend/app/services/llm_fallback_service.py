import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings
from app.schemas.mapping import FieldCandidate, FieldMapping, MappingEvidence
from app.schemas.target_schema import TargetField


@dataclass(frozen=True)
class LLMFallbackRequest:
    task_id: str
    field: TargetField
    candidates: list[FieldCandidate]


@dataclass(frozen=True)
class LLMFallbackSuggestion:
    candidate: FieldCandidate | None
    confidence: float
    reason: str
    model: str
    latency_ms: int
    prompt_hash: str
    response_hash: str
    error_code: str | None = None
    attempt_count: int = 1


class LLMFallbackAdapter(Protocol):
    enabled: bool
    model: str

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        ...


class DisabledLLMAdapter:
    enabled = False
    model = "disabled"

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        return None


class StubLLMAdapter:
    enabled = True
    model = "stub"

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        if not request.candidates:
            return None
        prompt = build_prompt(request)
        response = {
            "candidate_id": request.candidates[0].candidate_id,
            "confidence": 0.5,
            "reason": "Deterministic stub suggestion requires human review.",
        }
        return LLMFallbackSuggestion(
            candidate=request.candidates[0],
            confidence=0.5,
            reason=response["reason"],
            model=self.model,
            latency_ms=0,
            prompt_hash=hash_text(prompt),
            response_hash=hash_text(json.dumps(response, ensure_ascii=False, sort_keys=True)),
        )


class OpenAICompatibleLLMAdapter:
    enabled = True

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int = 0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def suggest(self, request: LLMFallbackRequest) -> LLMFallbackSuggestion | None:
        prompt = build_prompt(request)
        prompt_hash = hash_text(prompt)
        if not self.base_url or not self.api_key:
            return LLMFallbackSuggestion(
                candidate=None,
                confidence=0.5,
                reason="LLM fallback unavailable: missing API key or base URL.",
                model=self.model,
                latency_ms=0,
                prompt_hash=prompt_hash,
                response_hash=hash_text("missing_credentials"),
                error_code="missing_credentials",
            )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Suggest at most one source candidate for a target field. "
                        "Return compact JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        started = time.perf_counter()
        request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response_text = ""
        for attempt in range(self.max_retries + 1):
            http_request = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=request_body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    http_request,
                    timeout=self.timeout_seconds,
                ) as response:
                    response_text = response.read().decode("utf-8")
                break
            except (OSError, TimeoutError, urllib.error.URLError) as exc:
                if attempt < self.max_retries:
                    continue
                return LLMFallbackSuggestion(
                    candidate=None,
                    confidence=0.5,
                    reason=f"LLM fallback request failed: {exc.__class__.__name__}.",
                    model=self.model,
                    latency_ms=elapsed_ms(started),
                    prompt_hash=prompt_hash,
                    response_hash=hash_text(exc.__class__.__name__),
                    error_code="request_failed",
                    attempt_count=attempt + 1,
                )

        return self._parse_response(
            request,
            response_text,
            prompt_hash,
            started,
            attempt_count=attempt + 1,
        )

    def _parse_response(
        self,
        request: LLMFallbackRequest,
        response_text: str,
        prompt_hash: str,
        started: float,
        attempt_count: int = 1,
    ) -> LLMFallbackSuggestion:
        try:
            response_json = json.loads(response_text)
            content = response_json["choices"][0]["message"]["content"]
            suggestion_json = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return LLMFallbackSuggestion(
                candidate=None,
                confidence=0.5,
                reason="LLM fallback returned an unparsable response.",
                model=self.model,
                latency_ms=elapsed_ms(started),
                prompt_hash=prompt_hash,
                response_hash=hash_text(response_text),
                error_code="parse_failed",
                attempt_count=attempt_count,
            )

        candidate = self._select_candidate(request.candidates, suggestion_json)
        confidence = suggestion_json.get("confidence", 0.5)
        if not isinstance(confidence, int | float):
            confidence = 0.5
        reason = suggestion_json.get("reason")
        if not isinstance(reason, str) or not reason:
            reason = "LLM fallback suggestion requires human review."
        return LLMFallbackSuggestion(
            candidate=candidate,
            confidence=max(0.0, min(float(confidence), 0.65)),
            reason=reason,
            model=self.model,
            latency_ms=elapsed_ms(started),
            prompt_hash=prompt_hash,
            response_hash=hash_text(response_text),
            error_code=None if candidate is not None else "candidate_not_found",
            attempt_count=attempt_count,
        )

    @staticmethod
    def _select_candidate(
        candidates: list[FieldCandidate],
        suggestion_json: dict[str, Any],
    ) -> FieldCandidate | None:
        candidate_id = suggestion_json.get("candidate_id")
        source_path = suggestion_json.get("source_path")
        for candidate in candidates:
            if candidate.candidate_id == candidate_id or candidate.source_path == source_path:
                return candidate
        return None


class LLMFallbackService:
    def __init__(
        self,
        settings: Settings | None = None,
        adapter: LLMFallbackAdapter | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.adapter = adapter or self._adapter_from_settings(self.settings)

    def suggest_mapping(
        self,
        task_id: str,
        field: TargetField,
        candidates: list[FieldCandidate],
        used_source_paths: set[str],
        badcases: list[dict[str, Any]] | None = None,
        strict_failure: bool | None = None,
    ) -> FieldMapping | None:
        eligible_candidates = [
            candidate
            for candidate in candidates
            if candidate.source_path not in used_source_paths
            and not self._is_badcase_forbidden(
                candidate.source_name,
                field.field_id,
                badcases or [],
            )
        ]
        if not eligible_candidates or not self.adapter.enabled:
            return None

        suggestion = self.adapter.suggest(
            LLMFallbackRequest(task_id=task_id, field=field, candidates=eligible_candidates)
        )
        if suggestion is None:
            return None
        strict = self.settings.llm_strict_failure if strict_failure is None else strict_failure
        if suggestion.error_code and strict:
            raise RuntimeError(f"LLM fallback request failed: {suggestion.error_code}")
        candidate = suggestion.candidate or eligible_candidates[0]
        return FieldMapping(
            mapping_id=f"map_{task_id}_{field.field_id}_llm_fallback",
            task_id=task_id,
            candidate_id=candidate.candidate_id,
            source_field={
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
            },
            source_path=candidate.source_path,
            source_field_name=candidate.source_name,
            target_field_id=field.field_id,
            target_field_name=field.name,
            method="llm_fallback",
            strategy="llm_fallback",
            confidence=max(0.0, min(suggestion.confidence, 0.65)),
            confidence_tier="low",
            status="review_required",
            need_review=True,
            value_sample=candidate.value_sample,
            source_blocks=candidate.source_blocks,
            evidence=self._evidence(suggestion),
            evidence_text=self._evidence_text(suggestion),
            risk_flags=["llm_suggestion", "low_confidence"],
            badcase_filter={"checked": bool(badcases), "blocked": False, "reason": None},
            review_required_reason="LLM suggestions always require human review.",
            llm_metadata={
                "model": suggestion.model,
                "latency_ms": suggestion.latency_ms,
                "prompt_hash": suggestion.prompt_hash,
                "response_hash": suggestion.response_hash,
                "error_code": suggestion.error_code,
                "attempt_count": suggestion.attempt_count,
            },
        )

    def safe_config_snapshot(self, *, strict_failure: bool | None = None) -> dict[str, Any]:
        strict = self.settings.llm_strict_failure if strict_failure is None else strict_failure
        return {
            "enabled": (
                self.settings.llm_fallback_enabled and self.settings.llm_mode != "disabled"
            ),
            "mode": self.settings.llm_mode,
            "model": self.settings.llm_model,
            "timeout_seconds": self.settings.llm_timeout_seconds,
            "max_retries": self.settings.llm_max_retries,
            "max_suggestions_per_task": self.settings.llm_max_suggestions_per_task,
            "strict_failure": strict,
        }

    @staticmethod
    def _adapter_from_settings(settings: Settings) -> LLMFallbackAdapter:
        if not settings.llm_fallback_enabled or settings.llm_mode == "disabled":
            return DisabledLLMAdapter()
        if settings.llm_mode == "openai_compatible":
            return OpenAICompatibleLLMAdapter(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        return StubLLMAdapter()

    @staticmethod
    def _evidence(suggestion: LLMFallbackSuggestion) -> list[MappingEvidence]:
        evidence = [
            MappingEvidence(
                type="llm_suggestion",
                message="LLM fallback suggestion requires human review",
                weight=suggestion.confidence,
                source=suggestion.model,
            ),
            MappingEvidence(type="llm_metadata", message=f"adapter_model={suggestion.model}"),
            MappingEvidence(type="llm_metadata", message=f"latency_ms={suggestion.latency_ms}"),
            MappingEvidence(
                type="llm_metadata",
                message=f"attempt_count={suggestion.attempt_count}",
            ),
            MappingEvidence(type="llm_metadata", message=f"prompt_hash={suggestion.prompt_hash}"),
            MappingEvidence(
                type="llm_metadata",
                message=f"response_hash={suggestion.response_hash}",
            ),
            MappingEvidence(type="llm_reason", message=f"reason={suggestion.reason}"),
        ]
        if suggestion.error_code:
            evidence.append(
                MappingEvidence(
                    type="llm_error",
                    message=f"error_code={suggestion.error_code}",
                )
            )
        return evidence

    @staticmethod
    def _evidence_text(suggestion: LLMFallbackSuggestion) -> list[str]:
        return [item.message for item in LLMFallbackService._evidence(suggestion)]

    @staticmethod
    def _is_badcase_forbidden(
        source_name: str,
        target_field_id: str,
        badcases: list[dict[str, Any]],
    ) -> bool:
        for badcase in badcases:
            if badcase.get("source_field") != source_name:
                continue
            forbidden = badcase.get("forbidden_target_fields", [])
            if isinstance(forbidden, list) and target_field_id in forbidden:
                return True
        return False


def build_prompt(request: LLMFallbackRequest) -> str:
    payload = {
        "target_field": {
            "field_id": request.field.field_id,
            "name": request.field.name,
            "display_name": request.field.display_name,
            "type": request.field.type,
            "aliases": request.field.aliases,
        },
        "candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "source_path": candidate.source_path,
                "source_name": candidate.source_name,
                "display_name": candidate.display_name,
                "inferred_type": candidate.inferred_type,
                "value_sample": candidate.value_sample,
            }
            for candidate in request.candidates
        ],
        "output_contract": {
            "candidate_id": "candidate id or null",
            "source_path": "source path or null",
            "confidence": "0.0 to 0.65",
            "reason": "short reason; suggestion remains review_required",
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
