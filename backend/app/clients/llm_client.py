import json
import time
from typing import Any

import httpx

from app.config import Settings
from app.schemas.common import StrictBaseModel


class LLMSuggestion(StrictBaseModel):
    candidate_id: str
    target_field_id: str
    confidence: float
    reason: str


class LLMClient:
    def __init__(
        self,
        enabled: bool = False,
        mode: str = "mock",
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        prompt_version: str | None = None,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.enabled = enabled
        self.mode = mode
        self.base_url = base_url
        self.api_key = api_key
        self.model = model or "schema-mapping-model"
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.last_audit: dict[str, Any] = self._audit(
            status="disabled" if not enabled else "idle",
            suggestion_count=0,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMClient":
        enabled = settings.llm_mode != "disabled" and not settings.offline_mode
        return cls(
            enabled=enabled,
            mode=settings.llm_mode,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            prompt_version=settings.llm_prompt_version,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    def suggest_mappings(
        self,
        candidates: list[dict[str, Any]],
        target_fields: list[dict[str, Any]],
    ) -> list[LLMSuggestion]:
        if not self.enabled:
            self.last_audit = self._audit(status="disabled", suggestion_count=0)
            return []
        started = time.perf_counter()
        if not candidates or not target_fields:
            self.last_audit = self._audit(
                status="skipped",
                suggestion_count=0,
                latency_ms=self._elapsed_ms(started),
            )
            return []
        if self.mode != "mock":
            if self.mode == "openai_compatible":
                return self._suggest_openai_compatible(candidates, target_fields, started)
            self.last_audit = self._audit(
                status="failed",
                suggestion_count=0,
                latency_ms=self._elapsed_ms(started),
                error=f"unsupported llm mode: {self.mode}",
            )
            return []
        suggestions = [
            LLMSuggestion(
                candidate_id=str(candidates[0].get("candidate_id", "")),
                target_field_id=str(target_fields[0].get("field_id", "")),
                confidence=0.5,
                reason="mock suggestion",
            )
        ]
        self.last_audit = self._audit(
            status="success",
            suggestion_count=len(suggestions),
            latency_ms=self._elapsed_ms(started),
        )
        return suggestions

    def _suggest_openai_compatible(
        self,
        candidates: list[dict[str, Any]],
        target_fields: list[dict[str, Any]],
        started: float,
    ) -> list[LLMSuggestion]:
        if not self.base_url:
            self.last_audit = self._audit(
                status="failed",
                suggestion_count=0,
                latency_ms=self._elapsed_ms(started),
                error="llm_base_url is required",
            )
            return []
        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return JSON with a suggestions array. Each item must contain "
                        "candidate_id, target_field_id, confidence, and reason."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt_version": self.prompt_version,
                            "candidates": candidates,
                            "target_fields": target_fields,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        try:
            client_kwargs: dict[str, Any] = {"timeout": self.timeout_seconds}
            if self.transport is not None:
                client_kwargs["transport"] = self.transport
            with httpx.Client(**client_kwargs) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            suggestions = [
                LLMSuggestion.model_validate(item)
                for item in parsed.get("suggestions", [])
            ]
            self.last_audit = self._audit(
                status="success",
                suggestion_count=len(suggestions),
                latency_ms=self._elapsed_ms(started),
            )
            return suggestions
        except Exception as exc:
            self.last_audit = self._audit(
                status="failed",
                suggestion_count=0,
                latency_ms=self._elapsed_ms(started),
                error=str(exc),
            )
            return []

    def _audit(
        self,
        *,
        status: str,
        suggestion_count: int,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "status": status,
            "suggestion_count": suggestion_count,
            "latency_ms": latency_ms,
            "error": error,
        }

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((time.perf_counter() - started) * 1000))
