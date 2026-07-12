from __future__ import annotations

import pytest

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.schemas.topic5_execution import Topic5ExecutionOptions
from app.services.conversion_fingerprint_service import ConversionFingerprintService


def test_legacy_execution_options_warn_and_do_not_silently_execute_unknowns() -> None:
    options, warnings = Topic5ExecutionOptions.parse_legacy(
        {"mapping_mode": "global_assignment", "mystery_option": True}
    )

    assert options.mapping_mode == "global_assignment"
    assert "mystery_option" not in options.runtime_dict()
    assert {item["code"] for item in warnings} == {
        "legacy_options_deprecated",
        "unknown_legacy_option",
    }


def test_strict_execution_options_reject_unknown_and_conflicting_values() -> None:
    with pytest.raises(ValueError, match="unknown Topic 5 execution option"):
        Topic5ExecutionOptions.parse_legacy(
            {"strict_execution_options": True, "mystery_option": True}
        )
    with pytest.raises(ValueError, match="threshold values conflict"):
        Topic5ExecutionOptions.model_validate(
            {
                "thresholds": {"auto_accept": 0.8},
                "auto_accept_threshold": 0.9,
            }
        )


def test_conversion_fingerprint_ignores_task_ids_and_normalizes_line_endings() -> None:
    service = ConversionFingerprintService()
    first = service.hash_value(
        {"task_id": "task-a", "data": {"body": "one\r\ntwo"}}, semantic=True
    )
    second = service.hash_value(
        {"task_id": "task-b", "data": {"body": "one\ntwo"}}, semantic=True
    )

    assert first == second


def test_conversion_fingerprint_changes_for_semantic_configuration() -> None:
    base = {
        "uir": {"doc_id": "d", "blocks": [{"text": "body"}]},
        "target_schema": {"schema_id": "s", "fields": []},
        "metadata_template": None,
        "mapping_rules": {"aliases": {}},
        "content_organization": {"summary": {"document_mode": "extractive"}},
        "execution_options": {"mapping_mode": "global_assignment"},
    }
    first = ConversionFingerprintService.conversion_fingerprints(**base)
    changed = ConversionFingerprintService.conversion_fingerprints(
        **{
            **base,
            "execution_options": {"mapping_mode": "legacy"},
        }
    )

    assert first["conversion_fingerprint"] != changed["conversion_fingerprint"]


def test_inline_request_rejects_unknown_option_in_strict_migration_mode() -> None:
    from tests.topic5_helpers import announcement_convert_request

    payload = announcement_convert_request()
    payload["options"].update(
        {"strict_execution_options": True, "unknown_public_control": True}
    )

    with pytest.raises(ValueError, match="unknown Topic 5 execution option"):
        Topic5ConvertRequest.model_validate(payload)
