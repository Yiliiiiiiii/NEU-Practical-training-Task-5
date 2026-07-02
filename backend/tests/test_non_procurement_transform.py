from app.schemas.target_schema import TargetField
from app.services.transform_service import TransformService


def field(field_id: str, field_type: str) -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=field_type,
        required=False,
        aliases=[],
        constraints={},
    )


def test_normalizes_spaced_and_dotted_dates() -> None:
    service = TransformService()

    assert service._coerce_value("2026 年 7 月 1 日", field("publish_date", "date"), {}) == (
        "2026-07-01",
        None,
    )
    assert service._coerce_value("2026.7.1", field("meeting_date", "date"), {}) == (
        "2026-07-01",
        None,
    )


def test_splits_supported_array_fields_and_cleans_contact() -> None:
    service = TransformService()

    assert service._coerce_value("张三、李四；王五", field("attendees", "array[string]"), {}) == (
        ["张三", "李四", "王五"],
        None,
    )
    assert service._coerce_value(
        "市发改委、市财政局",
        field("departments", "array[string]"),
        {},
    ) == (["市发改委", "市财政局"], None)
    assert service._coerce_value("021 - 12345678", field("contact", "string"), {}) == (
        "021-12345678",
        None,
    )


def test_keeps_array_object_and_unlisted_arrays_unsplit() -> None:
    service = TransformService()

    assert service._coerce_value(
        "张三、李四；王五",
        field("action_items", "array[object]"),
        {},
    ) == (["张三、李四；王五"], None)
    assert service._coerce_value(
        "一等奖、二等奖",
        field("award_levels", "array[string]"),
        {},
    ) == (["一等奖、二等奖"], None)


def test_keeps_document_number_and_rejects_yearless_date() -> None:
    service = TransformService()

    assert service._coerce_value(
        "沪府办发〔2026〕12号",
        field("document_number", "string"),
        {},
    ) == (
        "沪府办发〔2026〕12号",
        None,
    )

    value, error = service._coerce_value("7月1日", field("publish_date", "date"), {})

    assert value == "7月1日"
    assert error is not None
    assert error["code"] == "date_format_error"


def test_rejects_invalid_calendar_dates() -> None:
    service = TransformService()

    value, error = service._coerce_value("2026.13.40", field("publish_date", "date"), {})

    assert value == "2026.13.40"
    assert error is not None
    assert error["code"] == "date_format_error"
