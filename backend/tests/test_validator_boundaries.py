from copy import deepcopy

import pytest

from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.chunks import Chunk, ChunksJSON
from app.schemas.content import ContentBlock, ContentJSON, ContentSchemaRef
from app.schemas.target_schema import TargetField, TargetSchema
from app.validators.consistency_validator import validate_consistency
from app.validators.content_validator import _check_type, validate_content_data
from app.validators.schema_validator import SchemaValidationError, validate_target_schema


def _schema() -> TargetSchema:
    fields = [
        TargetField(
            field_id="score",
            name="score",
            display_name="Score",
            type="integer",
            required=True,
        ),
        TargetField(
            field_id="label",
            name="label",
            display_name="Label",
            type="string",
            constraints={"enum": ["ok"], "pattern": "^[A-Z]+$", "max_length": 3},
        ),
        TargetField(
            field_id="short",
            name="short",
            display_name="Short",
            type="string",
            constraints={"min_length": 4},
        ),
    ]
    return TargetSchema(
        schema_id="schema_constraints",
        name="Constraints",
        version="1.0.0",
        fields=fields,
        json_schema={
            "type": "object",
            "required": ["score"],
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 20,
                    "exclusiveMinimum": 11,
                    "exclusiveMaximum": 19,
                },
                "label": {"type": "string"},
                "short": {"type": "string"},
            },
        },
    )


@pytest.mark.parametrize(
    ("value", "expected_type", "expected"),
    [
        ("text", "string", True),
        (1, "integer", True),
        (True, "int", False),
        (1.5, "number", True),
        (True, "float", False),
        (False, "boolean", True),
        ("2026-06-22", "date", True),
        ("2026-99-99", "date", False),
        (20260622, "date", False),
        ([], "array", True),
        ({}, "object", True),
        (object(), "custom", True),
    ],
)
def test_content_type_matrix(value, expected_type, expected):
    assert _check_type(value, expected_type) is expected


def test_content_validator_reports_all_supported_constraints():
    report = validate_content_data(
        task_id="task_constraints",
        schema_id="schema_constraints",
        data={"score": 9, "label": "toolong", "short": "x"},
        target_schema=_schema(),
    )

    codes = {issue.code for issue in report.issues}
    assert {
        "minimum_violation",
        "exclusive_minimum_violation",
        "enum_violation",
        "pattern_mismatch",
        "max_length_violation",
        "min_length_violation",
    } <= codes
    assert report.passed is False
    assert report.summary == {"error_count": 1, "warning_count": 5, "check_count": 6}


def test_content_validator_reports_upper_bounds_and_required_missing():
    upper = validate_content_data(
        "task_upper",
        "schema_constraints",
        {"score": 20, "label": "OK", "short": "long"},
        _schema(),
    )
    assert {issue.code for issue in upper.issues} == {
        "exclusive_maximum_violation",
        "enum_violation",
    }

    missing = validate_content_data(
        "task_missing",
        "schema_constraints",
        {"score": ""},
        _schema(),
    )
    assert [issue.code for issue in missing.issues] == ["required_missing"]


def _canonical() -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task_consistency",
        doc_id="doc_consistency",
        schema_id="schema_consistency",
        blocks=[
            CanonicalBlock(
                block_id="blk_1",
                type="heading",
                level=1,
                text="Title",
                source_blocks=["blk_1"],
            ),
            CanonicalBlock(
                block_id="blk_2",
                type="paragraph",
                text="Body",
                source_blocks=["blk_2"],
            ),
        ],
    )


def _content() -> ContentJSON:
    return ContentJSON(
        doc_id="doc_consistency",
        task_id="task_consistency",
        schema_ref=ContentSchemaRef(schema_id="schema_consistency", version="1.0.0"),
        blocks=[
            ContentBlock(block_id="blk_1", type="heading", text="Title"),
            ContentBlock(block_id="blk_2", type="paragraph", text="Body"),
        ],
    )


def _chunks() -> ChunksJSON:
    return ChunksJSON(
        doc_id="doc_consistency",
        task_id="task_consistency",
        chunks=[
            Chunk(chunk_id="chk_1", order=0, text="Title\nBody", source_blocks=["blk_1", "blk_2"])
        ],
    )


def test_consistency_validator_accepts_aligned_outputs():
    report = validate_consistency(
        "task_consistency",
        _content(),
        "<!-- block_id: blk_1 -->\nTitle\n<!-- block_id: blk_2 -->\nBody",
        _chunks(),
        _canonical(),
    )

    assert report.passed is True
    assert report.errors == []
    assert report.warnings == []


def test_consistency_validator_reports_every_cross_format_failure():
    content = deepcopy(_content())
    content.blocks = [
        ContentBlock(block_id="blk_extra", type="paragraph", text="Foreign"),
        ContentBlock(block_id="blk_1", type="heading", text="Changed"),
    ]
    chunks = deepcopy(_chunks())
    chunks.chunks[0].source_blocks = ["blk_orphan"]
    chunks.chunks[0].text = "Foreign text"

    report = validate_consistency(
        "task_consistency",
        content,
        "<!-- block_id: blk_2 -->\nBody\n<!-- block_id: blk_1 -->\nTitle",
        chunks,
        _canonical(),
    )

    codes = {issue.code for issue in report.errors}
    assert {
        "block_id_coverage",
        "block_order_consistency",
        "block_id_backlink",
        "block_text_consistency",
        "markdown_block_order_consistency",
        "chunk_source_blocks_backlink",
    } <= codes
    assert {issue.code for issue in report.warnings} == {"chunk_text_coverage"}
    assert report.passed is False


def test_consistency_validator_reports_missing_markdown_annotation():
    report = validate_consistency(
        "task_consistency",
        _content(),
        "<!-- block_id: blk_1 -->\nTitle",
        _chunks(),
        _canonical(),
    )
    assert "markdown_block_annotation" in {issue.code for issue in report.errors}


def test_schema_validator_rejects_non_object_json_schema():
    schema = _schema()
    schema.json_schema["type"] = "array"
    with pytest.raises(SchemaValidationError, match="must be object"):
        validate_target_schema(schema)
