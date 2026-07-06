import pytest

from app.schemas.target_schema import TargetField
from app.services.transform_service import TransformService


def date_field() -> TargetField:
    return TargetField(
        field_id="meeting_date",
        name="meeting_date",
        display_name="会议日期",
        type="date",
    )


@pytest.mark.parametrize(
    "source_value",
    [
        "2025年6月1日",
        "2025-06-01",
        "2025.6.1",
        "2025/06/01",
        "二〇二五年六月一日",
        "2025年6月1日下午",
    ],
)
def test_zh_date_normalizer_v2_supports_required_formats(source_value: str) -> None:
    normalized, error = TransformService()._coerce_value(
        source_value,
        date_field(),
        {},
    )

    assert normalized == "2025-06-01"
    assert error is None


def test_zh_date_normalizer_rejects_invalid_calendar_date() -> None:
    normalized, error = TransformService()._coerce_value(
        "二〇二五年十三月一日",
        date_field(),
        {},
    )

    assert normalized == "二〇二五年十三月一日"
    assert error is not None
    assert error["code"] == "date_format_error"

