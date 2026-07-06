import pytest

from app.config import Settings
from app.services.external_uir_adapter_service import ExternalUIRAdapterService
from app.services.external_uir_llm_service import ExternalUIRLLMSuggestionService


def sample_payload() -> dict:
    return {
        "id": "ext_proc_001",
        "title": "某采购项目中标公告",
        "chunks": [
            {"id": "c1", "type": "title", "text": "某采购项目中标公告"},
        ],
    }


def test_llm_disabled_by_default() -> None:
    _, report = ExternalUIRAdapterService().adapt_from_dict(
        sample_payload(),
        source_system="topic11",
    )

    assert report.status == "passed"
    assert all(item.strategy != "llm_suggestion" for item in report.trace_items)


def test_llm_suggestion_is_not_auto_accepted() -> None:
    with pytest.raises(ValueError, match="LLM suggestions are not implemented"):
        ExternalUIRAdapterService().adapt_from_dict(
            sample_payload(),
            source_system="topic11",
            allow_llm=True,
        )


class MockClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def chat_json(self, messages, *, timeout: int) -> dict:
        return self.payload


def test_mock_deepseek_valid_json_returns_assisted_suggestions() -> None:
    service = ExternalUIRLLMSuggestionService(
        Settings(external_uir_llm_enabled=True, deepseek_api_key="sk-test"),
        client=MockClient(
            {
                "suggestions": [
                    {
                        "external_path": "payload.title",
                        "target_uir_location": "metadata.title",
                        "operation": "preserve_title",
                        "confidence": 0.8,
                        "evidence": "title exists in source payload",
                        "review_required": True,
                        "reason": "External title can map to UIR metadata title",
                    }
                ],
                "warnings": [],
                "must_not_auto_accept_mapping": True,
                "must_not_activate_catalog": True,
            }
        ),
    )

    report = service.suggest_adapter_mappings(
        payload_excerpt=sample_payload(),
        unknown_paths=["payload.title"],
        dialect_hint="auto",
        source_system="topic11",
    )

    assert len(report.suggestions) == 1
    assert report.suggestions[0].external_path == "payload.title"
    assert report.must_not_auto_accept_mapping is True
    assert report.must_not_activate_catalog is True


def test_mock_deepseek_without_evidence_is_rejected_as_warning() -> None:
    service = ExternalUIRLLMSuggestionService(
        Settings(external_uir_llm_enabled=True, deepseek_api_key="sk-test"),
        client=MockClient(
            {
                "suggestions": [
                    {
                        "external_path": "payload.title",
                        "target_uir_location": "metadata.title",
                        "operation": "preserve_title",
                        "confidence": 0.8,
                        "evidence": "",
                        "review_required": True,
                        "reason": "missing evidence should be rejected",
                    }
                ],
                "warnings": [],
                "must_not_auto_accept_mapping": True,
                "must_not_activate_catalog": True,
            }
        ),
    )

    report = service.suggest_adapter_mappings(
        payload_excerpt=sample_payload(),
        unknown_paths=["payload.title"],
        dialect_hint="auto",
        source_system="topic11",
    )

    assert report.suggestions == []
    assert any("without evidence" in warning for warning in report.warnings)


def test_mock_deepseek_without_safety_flags_is_rejected() -> None:
    service = ExternalUIRLLMSuggestionService(
        Settings(external_uir_llm_enabled=True, deepseek_api_key="sk-test"),
        client=MockClient(
            {
                "suggestions": [],
                "warnings": [],
                "must_not_auto_accept_mapping": False,
                "must_not_activate_catalog": True,
            }
        ),
    )

    with pytest.raises(ValueError, match="must_not_auto_accept_mapping=true"):
        service.suggest_adapter_mappings(
            payload_excerpt=sample_payload(),
            unknown_paths=[],
            dialect_hint="auto",
            source_system="topic11",
        )


def test_deepseek_key_is_redacted_in_task_options() -> None:
    from app.utils.redaction import REDACTED, redact_sensitive_values

    redacted = redact_sensitive_values({"deepseek_api_key": "sk-secret"})

    assert redacted["deepseek_api_key"] == REDACTED
