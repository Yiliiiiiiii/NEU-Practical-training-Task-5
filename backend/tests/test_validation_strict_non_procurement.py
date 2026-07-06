from app.schemas.target_schema import TargetField, TargetSchema
from app.services.render_service import RenderedArtifacts
from app.services.validation_service import ValidationService


def schema(*fields: TargetField) -> TargetSchema:
    return TargetSchema(
        schema_id="strict_non_procurement",
        name="strict_non_procurement",
        version="1.0.0",
        fields=list(fields),
    )


def field(
    field_id: str,
    field_type: str,
    *,
    required: bool = False,
    enum: list[str] | None = None,
) -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=field_type,
        required=required,
        constraints={"enum": enum} if enum else {},
    )


def rendered(data: dict[str, object]) -> RenderedArtifacts:
    return RenderedArtifacts(
        structured_json={
            "data": data,
            "blocks": [{"block_id": "b1", "text": "正文"}],
        },
        markdown="# 文档\n",
        chunks=[{"chunk_id": "c1", "text": "正文", "source_block_ids": ["b1"]}],
    )


def test_validation_report_classifies_strict_failures() -> None:
    report = ValidationService().validate(
        task_id="task_strict",
        schema=schema(
            field("issuer", "string", required=True),
            field("publish_date", "date"),
            field("topics", "array[string]"),
            field("status", "enum", enum=["active"]),
        ),
        rendered=rendered(
            {
                "publish_date": "2025年6月1日",
                "topics": ["有效议题", 42],
                "status": "unknown",
            }
        ),
    )

    failures = {issue.failure_type: issue for issue in report.issues}
    assert report.passed is False
    assert report.schema_valid is False
    assert report.strict_semantic_valid is False
    assert {
        "missing_required",
        "date_format_invalid",
        "array_item_invalid",
        "enum_invalid",
    }.issubset(failures)
    assert failures["date_format_invalid"].source_value == "2025年6月1日"
    assert (
        failures["date_format_invalid"].suggested_normalized_value
        == "2025-06-01"
    )


def test_valid_non_procurement_payload_is_schema_and_semantically_valid() -> None:
    report = ValidationService().validate(
        task_id="task_valid",
        schema=schema(
            field("issuer", "string", required=True),
            field("publish_date", "date"),
            field("topics", "array[string]"),
        ),
        rendered=rendered(
            {
                "issuer": "工业和信息化部",
                "publish_date": "2025-06-01",
                "topics": ["议题一", "议题二"],
            }
        ),
    )

    assert report.passed is True
    assert report.schema_valid is True
    assert report.strict_semantic_valid is True
    assert report.issues == []
