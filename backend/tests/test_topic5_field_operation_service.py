from __future__ import annotations

import pytest

from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRBlock, UIRDocument
from app.services.field_operation_service import FieldOperationService
from app.services.transform_service import TransformService


def _uir() -> UIRDocument:
    return UIRDocument(
        uir_version="1.0",
        doc_id="field-operations",
        metadata={
            "title": "  Notice  ",
            "parts": "alpha; beta，gamma",
            "nested": {"owner": "OpenAI"},
            "date": "2026/07/10",
            "kind": "公告",
        },
        blocks=[
            UIRBlock(block_id="b1", type="paragraph", text="First"),
            UIRBlock(block_id="b2", type="paragraph", text="Second"),
        ],
    )


def _field(field_id: str, type_: str = "string") -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=type_,
    )


@pytest.mark.parametrize(
    ("rule", "field", "expected"),
    [
        (
            TransformRule(
                rule_id="rename",
                operation="rename",
                source_field="metadata.nested.owner",
                target_field_id="owner",
            ),
            _field("owner"),
            "OpenAI",
        ),
        (
            TransformRule(
                rule_id="merge",
                operation="merge",
                source_fields=["blocks.b1.text", "blocks.b2.text"],
                target_field_id="body",
                params={"separator": "\n", "skip_empty": True},
            ),
            _field("body", "text"),
            "First\nSecond",
        ),
        (
            TransformRule(
                rule_id="split",
                operation="split",
                source_field="metadata.parts",
                target_field_id="items",
                params={"separators": [";", "，"]},
            ),
            _field("items", "array[string]"),
            ["alpha", "beta", "gamma"],
        ),
        (
            TransformRule(
                rule_id="date",
                operation="normalize_date",
                source_field="metadata.date",
                target_field_id="publish_date",
            ),
            _field("publish_date", "date"),
            "2026-07-10",
        ),
        (
            TransformRule(
                rule_id="enum",
                operation="enum_map",
                source_field="metadata.kind",
                target_field_id="kind",
                params={"map": {"公告": "notice"}},
            ),
            _field("kind", "enum"),
            "notice",
        ),
        (
            TransformRule(
                rule_id="default",
                operation="default",
                target_field_id="language",
                params={"value": "zh-CN"},
            ),
            _field("language"),
            "zh-CN",
        ),
    ],
)
def test_field_operation_service_executes_supported_rules(
    rule: TransformRule,
    field: TargetField,
    expected: object,
) -> None:
    outcome = FieldOperationService().apply(
        rule=rule,
        uir=_uir(),
        target_field=field,
        current_value=None,
    )

    assert outcome.applied is True
    assert outcome.value == expected
    assert outcome.error is None


@pytest.mark.parametrize(
    "source_path",
    [
        "metadata.__class__",
        "metadata..owner",
        "metadata.items[0]",
        "system.secret",
        "blocks.b1.attributes.payload",
    ],
)
def test_field_operation_service_rejects_unsafe_source_paths(source_path: str) -> None:
    rule = TransformRule(
        rule_id="unsafe",
        operation="rename",
        source_field=source_path,
        target_field_id="value",
    )

    outcome = FieldOperationService().apply(
        rule=rule,
        uir=_uir(),
        target_field=_field("value"),
        current_value=None,
    )

    assert outcome.applied is False
    assert outcome.error == "unsafe_source_path"


def test_field_operation_service_rejects_unsupported_operation() -> None:
    rule = TransformRule(
        rule_id="execute",
        operation="python_eval",
        target_field_id="value",
        params={"expression": "open('secret')"},
    )

    outcome = FieldOperationService().apply(
        rule=rule,
        uir=_uir(),
        target_field=_field("value"),
        current_value=None,
    )

    assert outcome.applied is False
    assert outcome.error == "unsupported_operation"


def test_transform_service_applies_rules_after_mapped_values() -> None:
    schema = TargetSchema(
        schema_id="operations",
        name="Operations",
        version="1.0.0",
        fields=[_field("body", "text"), _field("items", "array[string]")],
    )
    template = MappingTemplate(
        template_id="operations-v1",
        schema_id="operations",
        name="Operations",
        version="1.0.0",
        transform_rules=[
            TransformRule(
                rule_id="body-merge",
                operation="merge",
                source_fields=["blocks.b1.text", "blocks.b2.text"],
                target_field_id="body",
            ),
            TransformRule(
                rule_id="items-split",
                operation="split",
                source_field="metadata.parts",
                target_field_id="items",
                params={"separators": [";", "，"]},
            ),
        ],
    )
    mapping_report = MappingReport(
        task_id="task",
        schema_id="operations",
        summary={},
        mappings=[],
    )

    result = TransformService().transform(
        "task", _uir(), schema, template, mapping_report
    )

    assert result.data == {
        "body": "First\nSecond",
        "items": ["alpha", "beta", "gamma"],
    }
    assert [trace["rule_id"] for trace in result.report["traces"]] == [
        "body-merge",
        "items-split",
    ]


def test_transform_service_records_unsafe_rule_without_applying_it() -> None:
    schema = TargetSchema(
        schema_id="operations",
        name="Operations",
        version="1.0.0",
        fields=[_field("body", "text")],
    )
    template = MappingTemplate(
        template_id="operations-v1",
        schema_id="operations",
        name="Operations",
        version="1.0.0",
        transform_rules=[
            TransformRule(
                rule_id="unsafe",
                operation="python_eval",
                target_field_id="body",
            )
        ],
    )
    mapping_report = MappingReport(
        task_id="task",
        schema_id="operations",
        summary={},
        mappings=[],
    )

    result = TransformService().transform(
        "task", _uir(), schema, template, mapping_report
    )

    assert "body" not in result.data
    assert result.report["errors"][0]["code"] == "unsupported_operation"
