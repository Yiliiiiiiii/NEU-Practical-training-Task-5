from __future__ import annotations

import json
from pathlib import Path

from app.schemas.topic5_convert import Topic5ConvertRequest
from app.services.topic5_conversion_service import Topic5ConversionService

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_mode_remains_default_for_topic5_conversion(tmp_path: Path) -> None:
    payload = json.loads(
        (ROOT / "examples" / "topic5_inline" / "event_notice_convert_request.json").read_text(
            encoding="utf-8"
        )
    )
    payload["options"].pop("mapping_mode", None)

    response = Topic5ConversionService(tmp_path).convert(
        Topic5ConvertRequest.model_validate(payload)
    )

    assert response.mapping_report["summary"].get("mapping_mode", "legacy") == "legacy"


def test_topic5_conversion_supports_global_assignment_mode(tmp_path: Path) -> None:
    payload = json.loads(
        (ROOT / "examples" / "topic5_inline" / "event_notice_convert_request.json").read_text(
            encoding="utf-8"
        )
    )
    payload["options"]["mapping_mode"] = "global_assignment"

    response = Topic5ConversionService(tmp_path).convert(
        Topic5ConvertRequest.model_validate(payload)
    )

    assert response.mapping_report["summary"]["mapping_mode"] == "global_assignment"
    assert response.mapping_report["summary"]["pair_count"] > 0
    assert response.mapping_report["mappings"]


def test_topic5_conversion_returns_mapping_repair_report_when_enabled(tmp_path: Path) -> None:
    payload = json.loads(
        (ROOT / "examples" / "topic5_inline" / "event_notice_convert_request.json").read_text(
            encoding="utf-8"
        )
    )
    payload["options"]["enable_mapping_repair"] = True

    response = Topic5ConversionService(tmp_path).convert(
        Topic5ConvertRequest.model_validate(payload)
    )

    assert response.mapping_repair_report is not None
    assert response.mapping_repair_report["enabled"] is True
