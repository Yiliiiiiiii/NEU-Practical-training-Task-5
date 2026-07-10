from __future__ import annotations

from app.schemas.target_schema import TargetField, TargetSchema
from app.services.render_service import RenderedArtifacts
from app.services.validation_service import ValidationService


def _schema(field: TargetField) -> TargetSchema:
    return TargetSchema(
        schema_id="localization",
        name="Localization",
        version="1.0.0",
        fields=[field],
    )


def _rendered(value: object = None, *, include: bool = True) -> RenderedArtifacts:
    data = {"subject": value} if include else {}
    return RenderedArtifacts(
        structured_json={
            "data": data,
            "blocks": [{"block_id": "b1", "text": "source"}],
        },
        markdown="# content\n",
        chunks=[{"chunk_id": "c1", "text": "source", "source_block_ids": ["b1"]}],
    )


def test_required_issue_has_exact_stage_path_and_code() -> None:
    field = TargetField(
        field_id="subject",
        name="subject",
        display_name="Subject",
        type="string",
        required=True,
    )

    issue = ValidationService().validate(
        "task", _schema(field), _rendered(include=False)
    ).issues[0]

    assert (issue.stage, issue.path, issue.code) == (
        "schema_validation",
        "data.subject",
        "required_field_missing",
    )


def test_nested_object_issue_has_exact_nested_path() -> None:
    field = TargetField(
        field_id="subject",
        name="subject",
        display_name="Subject",
        type="object",
        constraints={
            "properties": {"owner": {"type": "string", "required": True}},
            "additional_properties": False,
        },
    )

    report = ValidationService().validate(
        "task", _schema(field), _rendered({"unexpected": "value"})
    )
    triples = {(issue.stage, issue.path, issue.code) for issue in report.issues}

    assert (
        "schema_validation",
        "data.subject.owner",
        "nested_required_missing",
    ) in triples
    assert (
        "schema_validation",
        "data.subject.unexpected",
        "unexpected_field",
    ) in triples


def test_scalar_constraints_are_localized() -> None:
    field = TargetField(
        field_id="subject",
        name="subject",
        display_name="Subject",
        type="string",
        constraints={"min_length": 5, "pattern": r"^[A-Z]+$"},
    )

    report = ValidationService().validate(
        "task", _schema(field), _rendered("bad")
    )
    triples = {(issue.stage, issue.path, issue.code) for issue in report.issues}

    assert ("schema_validation", "data.subject", "min_length_violation") in triples
    assert ("schema_validation", "data.subject", "pattern_mismatch") in triples
