import json
from pathlib import Path

import pytest

from app.engines.mapping_engine import MappingEngine
from app.engines.transform_engine import TransformEngine
from app.schemas.canonical import CanonicalModel
from app.schemas.chunks import ChunksJSON
from app.schemas.content import ContentJSON
from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRDocument
from app.validators.consistency_validator import validate_consistency
from app.validators.content_validator import validate_content_data

BADCASES = Path(__file__).resolve().parents[2] / "examples" / "badcases"
CASE_NAMES = [
    "badcase_missing_required.json",
    "badcase_type_error.json",
    "badcase_mapping_ambiguous.json",
    "badcase_broken_block_link.json",
]


def load_case(name: str) -> dict:
    return json.loads((BADCASES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", CASE_NAMES)
def test_badcase_fixture_contract(name):
    case = load_case(name)

    assert set(case) == {"case_id", "description", "input", "expected"}
    assert case["case_id"] == Path(name).stem
    assert isinstance(case["description"], str) and case["description"]
    assert isinstance(case["input"], dict)
    assert set(case["expected"]) >= {
        "error_code",
        "task_status",
        "trace_action",
    }


def test_missing_required_badcase_produces_validation_error():
    case = load_case("badcase_missing_required.json")
    schema = TargetSchema.model_validate(case["input"]["schema"])

    report = validate_content_data(
        case["input"]["task_id"],
        schema.schema_id,
        case["input"]["data"],
        schema,
    )

    assert not report.passed
    assert any(issue.code == case["expected"]["issue_code"] for issue in report.issues)


def test_type_error_badcase_records_failed_transform_trace():
    case = load_case("badcase_type_error.json")
    fields, traces, errors = TransformEngine().execute(
        uir=UIRDocument.model_validate(case["input"]["uir"]),
        mappings=[FieldMapping.model_validate(case["input"]["mapping"])],
        transform_rules=[TransformRule.model_validate(case["input"]["rule"])],
        enum_maps={},
        defaults={},
    )

    assert fields["count"].value == "not-an-integer"
    assert errors
    assert any(
        trace["action"] == case["expected"]["trace_action"]
        and trace["status"] == case["expected"]["trace_status"]
        for trace in traces
    )


def test_ambiguous_mapping_badcase_requires_review():
    case = load_case("badcase_mapping_ambiguous.json")
    mappings = MappingEngine().map_fields(
        task_id=case["input"]["task_id"],
        candidates=[FieldCandidate.model_validate(case["input"]["candidate"])],
        target_schema=TargetSchema.model_validate(case["input"]["schema"]),
        template=MappingTemplate.model_validate(case["input"]["template"]),
        review_threshold=case["input"]["review_threshold"],
    )

    assert mappings
    assert any(mapping.need_review for mapping in mappings)


def test_broken_block_link_badcase_fails_consistency():
    case = load_case("badcase_broken_block_link.json")
    report = validate_consistency(
        task_id=case["input"]["task_id"],
        canonical=CanonicalModel.model_validate(case["input"]["canonical"]),
        content_json=ContentJSON.model_validate(case["input"]["content_json"]),
        content_md=case["input"]["content_md"],
        chunks=ChunksJSON.model_validate(case["input"]["chunks"]),
    )

    assert not report.passed
    assert any(
        issue.code == case["expected"]["issue_code"] for issue in report.errors
    )
