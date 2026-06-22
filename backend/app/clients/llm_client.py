from typing import Any

from app.schemas.common import StrictBaseModel


class LLMSuggestion(StrictBaseModel):
    candidate_id: str
    target_field_id: str
    confidence: float
    reason: str


class LLMClient:
    def __init__(self, enabled: bool = False, mode: str = "mock") -> None:
        self.enabled = enabled
        self.mode = mode

    def suggest_mappings(
        self,
        candidates: list[dict[str, Any]],
        target_fields: list[dict[str, Any]],
    ) -> list[LLMSuggestion]:
        if not self.enabled:
            return []
        if self.mode != "mock":
            raise NotImplementedError("only mock LLM suggestions are available in Phase 4")
        if not candidates or not target_fields:
            return []
        return [
            LLMSuggestion(
                candidate_id=str(candidates[0].get("candidate_id", "")),
                target_field_id=str(target_fields[0].get("field_id", "")),
                confidence=0.5,
                reason="mock suggestion",
            )
        ]
