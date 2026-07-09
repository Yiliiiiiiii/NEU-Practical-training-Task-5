from __future__ import annotations

import json
from pathlib import Path

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.topic5_conversion_service import Topic5ConversionService

ROOT = Path(__file__).resolve().parents[2]


def test_topic5_event_notice_no_code_conversion_passes(tmp_path):
    payload = json.loads(
        (ROOT / "examples" / "topic5_inline" / "event_notice_convert_request.json")
        .read_text(encoding="utf-8")
    )
    request = Topic5ConvertRequest.model_validate(payload)

    response = Topic5ConversionService(tmp_path).convert(request, create_package=True)

    assert response.status == "completed"
    assert response.schema_id == "event_notice_doc"
    assert response.mapping_report["summary"]["mapping_input_name"] == "mapping_rules"
    assert response.mapping_report["summary"]["required_unmapped_count"] == 0
    assert response.mapping_report["summary"]["review_required_count"] == 0
    assert response.mapping_report["summary"].get("llm_suggestion_count", 0) == 0
    assert response.validation_report["passed"] is True
    assert response.verifier_report is not None
    assert response.verifier_report["passed"] is True
