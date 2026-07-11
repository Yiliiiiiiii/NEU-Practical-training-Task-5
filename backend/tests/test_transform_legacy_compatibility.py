from app.schemas.api import TaskCreateRequest
from app.schemas.external_uir import ExternalUIRCreateTaskRequest
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.topic5_convert import Topic5ConvertRequest
from app.schemas.uir import UIRDocument
from app.services.transform_service import TransformService


def field(field_id: str, field_type: str = "string") -> TargetField:
    return TargetField(
        field_id=field_id,
        name=field_id,
        display_name=field_id,
        type=field_type,
        constraints={"enum": ["policy", "notice"]} if field_type == "enum" else {},
    )


def test_legacy_business_heuristics_are_disabled_by_default() -> None:
    service = TransformService()

    assert service._coerce_value("policy_doc", field("doc_type", "enum"), {}) == (
        "policy_doc",
        None,
    )
    assert service._coerce_value(
        "A、B；C", field("attendees", "array[string]"), {}
    ) == (["A、B；C"], None)
    assert service._coerce_value("010 - 1234", field("contact"), {}) == (
        "010 - 1234",
        None,
    )
    assert service._coerce_value("来源：Example Bureau网站", field("issuer"), {}) == (
        "来源：Example Bureau网站",
        None,
    )


def test_legacy_business_heuristics_require_explicit_opt_in() -> None:
    service = TransformService()

    assert service._coerce_value(
        "policy_doc",
        field("doc_type", "enum"),
        {},
        enable_legacy_transform_heuristics=True,
    ) == ("policy", None)
    assert service._coerce_value(
        "A、B；C",
        field("attendees", "array[string]"),
        {},
        enable_legacy_transform_heuristics=True,
    ) == (["A", "B", "C"], None)
    assert service._coerce_value(
        "010 - 1234",
        field("contact"),
        {},
        enable_legacy_transform_heuristics=True,
    ) == ("010-1234", None)


def test_transform_report_records_legacy_heuristic_use() -> None:
    schema = TargetSchema(
        schema_id="compat_doc",
        name="compat",
        version="1.0.0",
        fields=[field("contact")],
    )
    template = MappingTemplate(
        template_id="compat_v1",
        name="compat",
        schema_id="compat_doc",
        version="1.0.0",
    )
    report = MappingReport(
        task_id="task_compat",
        schema_id="compat_doc",
        summary={},
        mappings=[
            {
                "target_field_id": "contact",
                "source_field": "contact",
                "value_sample": "010 - 1234",
            }
        ],
    )
    uir = UIRDocument(uir_version="1.0", doc_id="doc_compat", blocks=[])

    result = TransformService().transform(
        task_id="task_compat",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=report,
        enable_legacy_transform_heuristics=True,
    )

    assert result.report["warnings"] == [
        {
            "code": "legacy_transform_heuristic_used",
            "message": "Legacy transform heuristics were applied.",
            "target_field_ids": ["contact"],
        }
    ]
    assert result.report["traces"][0]["legacy_heuristic"] == "contact_cleanup"


def test_declared_enum_mapping_is_not_reported_as_legacy_heuristic() -> None:
    schema = TargetSchema(
        schema_id="declared_doc",
        name="declared",
        version="1.0.0",
        fields=[field("doc_type", "enum")],
    )
    template = MappingTemplate(
        template_id="declared_v1",
        name="declared",
        schema_id="declared_doc",
        version="1.0.0",
        enum_maps={"doc_type": {"notice label": "notice"}},
    )
    report = MappingReport(
        task_id="task_declared",
        schema_id="declared_doc",
        summary={},
        mappings=[
            {
                "target_field_id": "doc_type",
                "source_field": "type",
                "value_sample": "notice label",
            }
        ],
    )

    result = TransformService().transform(
        task_id="task_declared",
        uir=UIRDocument(uir_version="1.0", doc_id="doc_declared", blocks=[]),
        schema=schema,
        template=template,
        mapping_report=report,
        enable_legacy_transform_heuristics=True,
    )

    assert result.data["doc_type"] == "notice"
    assert result.report["warnings"] == []
    assert "legacy_heuristic" not in result.report["traces"][0]


def test_topic5_entry_points_expose_typed_default_off_flag() -> None:
    assert TaskCreateRequest(
        doc_id="doc", schema_id="schema", template_id="template"
    ).enable_legacy_transform_heuristics is False
    assert ExternalUIRCreateTaskRequest(
        doc_id="doc", schema_id="schema", template_id="template"
    ).enable_legacy_transform_heuristics is False

    schema = TargetSchema(
        schema_id="schema",
        name="schema",
        version="1.0.0",
        fields=[field("title")],
    )
    request = Topic5ConvertRequest(
        uir=UIRDocument(uir_version="1.0", doc_id="doc", blocks=[]),
        target_schema=schema,
        mapping_rules=MappingTemplate(
            template_id="template",
            name="template",
            schema_id="schema",
            version="1.0.0",
        ),
    )
    assert request.enable_legacy_transform_heuristics is False
