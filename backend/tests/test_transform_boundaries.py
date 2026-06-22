import pytest

from app.engines.transform_engine import TransformEngine
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRBlock, UIRDocument


def _uir() -> UIRDocument:
    return UIRDocument(
        uir_version="1.0",
        doc_id="doc_transform_boundaries",
        metadata={"known": "value"},
        blocks=[
            UIRBlock(
                block_id="blk_1",
                type="paragraph",
                text="Body",
                attributes={"kind": "notice"},
            )
        ],
    )


def _execute(rule: TransformRule):
    return TransformEngine().execute(_uir(), [], [rule], {}, {})


def test_transform_unknown_operation_is_recorded():
    rule = TransformRule(
        rule_id="unknown",
        operation="not_supported",
        target_field_id="target",
    )

    fields, traces, errors = _execute(rule)

    assert fields == {}
    assert errors == ["rule unknown: unknown operation: not_supported"]
    assert traces[0]["status"] == "error"


def test_transform_on_error_raise_propagates_rule_failure():
    rule = TransformRule(
        rule_id="strict",
        operation="rename",
        target_field_id="target",
        on_error="raise",
    )

    with pytest.raises(ValueError, match="rename rule has no source_field"):
        _execute(rule)


@pytest.mark.parametrize(
    "operation",
    ["rename", "type_cast", "date_format", "enum_map", "default", "merge"],
)
def test_transform_operations_without_scalar_target_are_noops(operation):
    rule = TransformRule(
        rule_id=f"empty_{operation}",
        operation=operation,
        target_fields=["only_for_validation"],
    )

    fields, traces, errors = _execute(rule)

    assert fields == {}
    assert traces == []
    assert errors == []


def test_merge_can_reuse_values_and_keep_empty_parts_when_requested():
    engine = TransformEngine()
    values = {
        "first": {
            "value": "A",
            "type": "string",
            "candidate_ids": [],
            "source_blocks": [],
        },
        "empty": {
            "value": None,
            "type": "string",
            "candidate_ids": [],
            "source_blocks": [],
        },
    }
    traces = []
    rule = TransformRule(
        rule_id="merge_values",
        operation="merge",
        source_fields=["first", "metadata.empty", "missing"],
        target_field_id="joined",
        params={"separator": "|", "skip_empty": False},
    )

    engine._apply_rule(rule, values, {}, _uir(), {}, traces)

    assert values["joined"]["value"] == "A||"
    assert traces[0]["status"] == "success"


def test_split_can_reuse_existing_value_and_handle_no_targets():
    engine = TransformEngine()
    values = {
        "compound": {
            "value": "left|right",
            "type": "string",
            "candidate_ids": [],
            "source_blocks": [],
        }
    }
    traces = []
    rule = TransformRule(
        rule_id="split_no_targets",
        operation="split",
        source_field="compound",
        target_field_id="validation_target",
    )

    engine._apply_rule(rule, values, {}, _uir(), {}, traces)

    assert traces[0]["target_field_id"] is None
    assert traces[0]["reason"] == "split into 0 fields"


def test_split_without_source_is_recorded_as_error():
    rule = TransformRule(
        rule_id="split_no_source",
        operation="split",
        target_fields=["left"],
    )

    _, traces, errors = _execute(rule)

    assert errors == ["rule split_no_source: split rule has no source_field"]
    assert traces[0]["action"] == "split"


def test_source_resolution_supports_block_attributes_and_text():
    engine = TransformEngine()
    uir = _uir()

    assert engine._resolve_source(uir, "blocks.blk_1.attributes.kind") == "notice"
    assert engine._resolve_source(uir, "blocks.blk_1.text") == "Body"
    assert engine._resolve_source(uir, "blocks.unknown.text") is None
    assert engine._resolve_source(uir, "unsupported.path") is None


def test_value_source_resolution_supports_metadata_alias_and_missing():
    engine = TransformEngine()
    values = {"name": {"value": "Direct"}, "title": {"value": "Metadata alias"}}

    assert engine._get_value_from_source("name", values) == "Direct"
    assert engine._get_value_from_source("metadata.title", values) == "Metadata alias"
    assert engine._get_value_from_source("blocks.none.text", values) is None


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (True, "bool"),
        (1, "integer"),
        (1.5, "float"),
        ("2026-06-22", "date"),
        ("text", "string"),
        (None, "string"),
    ],
)
def test_transform_type_inference(value, expected_type):
    assert TransformEngine._infer_type(value) == expected_type


@pytest.mark.parametrize(
    ("value", "target", "expected"),
    [
        (None, "string", None),
        (42, "string", "42"),
        ("1,234", "integer", 1234),
        ("1,234.5", "float", 1234.5),
        (True, "bool", True),
        ("yes", "bool", True),
        ("no", "bool", False),
        ("2026/06/22", "date", "2026-06-22"),
    ],
)
def test_transform_cast_matrix(value, target, expected):
    assert TransformEngine._cast_value(value, target) == expected


def test_transform_cast_rejects_invalid_values_and_types():
    with pytest.raises(ValueError, match="cannot cast"):
        TransformEngine._cast_value("maybe", "bool")
    with pytest.raises(ValueError, match="cannot cast"):
        TransformEngine._cast_value("not-a-date", "date")
    with pytest.raises(ValueError, match="unsupported target type"):
        TransformEngine._cast_value("value", "binary")


def test_date_conversion_handles_invalid_chinese_date_and_compatibility_wrapper():
    invalid = "2026\u5e7413\u670840\u65e5"
    assert TransformEngine._try_convert_date(invalid) == (invalid, False)
    assert TransformEngine._convert_date("20260622") == "2026-06-22"
