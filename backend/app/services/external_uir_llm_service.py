import json
from typing import Any, Protocol

from app.config import Settings
from app.schemas.external_uir import (
    ExternalUIRLLMSuggestion,
    ExternalUIRLLMSuggestionReport,
)
from app.services.deepseek_client import DeepSeekClient


class JSONChatClient(Protocol):
    def chat_json(self, messages: list[dict[str, str]], *, timeout: int) -> dict[str, Any]:
        ...


class ExternalUIRLLMSuggestionService:
    def __init__(
        self,
        settings: Settings,
        client: JSONChatClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or DeepSeekClient(settings)

    def suggest_adapter_mappings(
        self,
        payload_excerpt: dict[str, Any],
        unknown_paths: list[str],
        dialect_hint: str | None,
        source_system: str,
    ) -> ExternalUIRLLMSuggestionReport:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a structure mapping assistant for External UIR Adapter. "
                    "Only produce suggestions grounded in source paths and values present "
                    "in the input JSON. Do not invent fields, create schemas, activate "
                    "catalog entries, or accept mappings. Return a JSON object only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "source_system": source_system,
                        "dialect_hint": dialect_hint,
                        "unknown_paths": unknown_paths,
                        "payload_excerpt": self._limited_payload(payload_excerpt),
                        "required_output": {
                            "suggestions": [
                                {
                                    "external_path": "payload.path",
                                    "target_uir_location": "blocks[].text",
                                    "operation": "create_paragraph_block",
                                    "confidence": 0.0,
                                    "evidence": "source value evidence",
                                    "review_required": True,
                                    "reason": "why this suggestion is plausible",
                                }
                            ],
                            "warnings": [],
                            "must_not_auto_accept_mapping": True,
                            "must_not_activate_catalog": True,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        raw = self.client.chat_json(
            messages,
            timeout=self.settings.deepseek_timeout_seconds,
        )
        return self._validate_report(raw, payload_excerpt)

    def _validate_report(
        self,
        raw: dict[str, Any],
        payload: dict[str, Any],
    ) -> ExternalUIRLLMSuggestionReport:
        if raw.get("must_not_auto_accept_mapping") is not True:
            raise ValueError("LLM response must set must_not_auto_accept_mapping=true")
        if raw.get("must_not_activate_catalog") is not True:
            raise ValueError("LLM response must set must_not_activate_catalog=true")

        raw_suggestions = raw.get("suggestions", [])
        if not isinstance(raw_suggestions, list):
            raise ValueError("LLM response suggestions must be a list")
        max_suggestions = self.settings.deepseek_max_suggestions_per_request
        if len(raw_suggestions) > max_suggestions:
            raise ValueError("LLM response exceeded max suggestions")

        suggestions: list[ExternalUIRLLMSuggestion] = []
        warnings = [str(item) for item in raw.get("warnings", []) if isinstance(item, str)]
        for item in raw_suggestions:
            if not isinstance(item, dict):
                warnings.append("ignored non-object LLM suggestion")
                continue
            external_path = item.get("external_path")
            evidence = item.get("evidence")
            if not isinstance(external_path, str) or not external_path:
                warnings.append("ignored LLM suggestion without external_path")
                continue
            if not isinstance(evidence, str) or not evidence:
                warnings.append(f"ignored LLM suggestion without evidence: {external_path}")
                continue
            if not self._external_path_exists(payload, external_path):
                warnings.append(f"ignored LLM suggestion for missing path: {external_path}")
                continue
            suggestions.append(ExternalUIRLLMSuggestion.model_validate(item))

        return ExternalUIRLLMSuggestionReport(
            suggestions=suggestions,
            warnings=warnings,
            must_not_auto_accept_mapping=True,
            must_not_activate_catalog=True,
        )

    def _limited_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) <= 12000:
            return payload
        return {"payload_excerpt_truncated": encoded[:12000]}

    def _external_path_exists(self, payload: dict[str, Any], path: str) -> bool:
        normalized = path.removeprefix("$.")
        if normalized == "$":
            return True
        if normalized.startswith("payload."):
            normalized = normalized[len("payload.") :]
        elif normalized == "payload":
            return True
        current: Any = payload
        for part in normalized.split("."):
            if not part:
                return False
            name, indexes = self._split_indexes(part)
            if name:
                if not isinstance(current, dict) or name not in current:
                    return False
                current = current[name]
            for index in indexes:
                if not isinstance(current, list) or index >= len(current):
                    return False
                current = current[index]
        return True

    @staticmethod
    def _split_indexes(part: str) -> tuple[str, list[int]]:
        if "[" not in part:
            return part, []
        name = part.split("[", 1)[0]
        indexes: list[int] = []
        tail = part[len(name) :]
        while tail:
            if not tail.startswith("[") or "]" not in tail:
                return part, []
            raw_index, tail = tail[1:].split("]", 1)
            if not raw_index.isdigit():
                return part, []
            indexes.append(int(raw_index))
        return name, indexes
