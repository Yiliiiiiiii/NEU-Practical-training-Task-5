from __future__ import annotations

from app.schemas.metadata_template import MetadataTemplateConfig
from app.schemas.uir import UIRDocument
from app.services.metadata_template_service import MetadataTemplateService


def _uir(metadata: dict | None = None) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc-1",
            "metadata": metadata or {},
            "blocks": [],
        }
    )


def _template(*fields: dict) -> MetadataTemplateConfig:
    return MetadataTemplateConfig.model_validate(
        {
            "template_id": "metadata-v1",
            "schema_id": "example_doc",
            "version": "1.2.0",
            "metadata_fields": list(fields),
        }
    )


def _render(
    template: MetadataTemplateConfig,
    *,
    metadata: dict | None = None,
    transformed_fields: dict | None = None,
):
    return MetadataTemplateService().render(
        uir=_uir(metadata),
        transformed_fields=transformed_fields or {},
        template=template,
        system_context={
            "doc_id": "doc-1",
            "schema_id": "example_doc",
            "schema_version": "1.0.0",
            "template_id": "mapping-v1",
            "template_version": "1.0.0",
            "metadata_template_id": template.template_id,
            "metadata_template_version": template.version,
        },
    )


def test_same_name_resolves_from_uir_metadata_before_transformed_fields() -> None:
    result = _render(
        _template({"field_id": "language", "type": "string"}),
        metadata={"language": "zh-CN"},
        transformed_fields={"language": "en-US"},
    )

    assert result.document_metadata == {"language": "zh-CN"}
    assert result.report.field_traces[0].source.path == "uir.metadata.language"


def test_same_name_falls_back_to_transformed_fields() -> None:
    result = _render(
        _template({"field_id": "language", "type": "string"}),
        transformed_fields={"language": "en-US"},
    )

    assert result.document_metadata == {"language": "en-US"}
    assert result.report.field_traces[0].source.kind == "transformed_field"


def test_explicit_nested_source_path_is_resolved_without_expression_evaluation() -> None:
    result = _render(
        _template(
            {
                "field_id": "department",
                "type": "string",
                "source_path": "uir.metadata.governance.department",
            }
        ),
        metadata={"governance": {"department": "IT"}},
    )

    assert result.document_metadata == {"department": "IT"}
    assert result.report.field_traces[0].source.path == (
        "uir.metadata.governance.department"
    )


def test_default_is_used_and_traced_when_source_is_missing() -> None:
    result = _render(
        _template(
            {
                "field_id": "language",
                "type": "string",
                "default": "zh-CN",
            }
        )
    )

    assert result.document_metadata == {"language": "zh-CN"}
    assert result.report.defaults_used == ["language"]
    assert result.report.field_traces[0].default_used is True
    assert result.report.field_traces[0].source.kind == "default"


def test_explicit_system_value_is_resolved_and_traced() -> None:
    result = _render(
        _template(
            {
                "field_id": "source_doc_id",
                "type": "string",
                "source_path": "system.doc_id",
            }
        )
    )

    assert result.document_metadata == {"source_doc_id": "doc-1"}
    assert result.report.field_traces[0].source.kind == "system"


def test_required_missing_field_is_localized_and_not_filled_with_null() -> None:
    result = _render(
        _template({"field_id": "classification", "type": "string", "required": True})
    )

    assert result.passed is False
    assert "classification" not in result.document_metadata
    assert result.report.missing_required_fields == ["classification"]
    assert result.report.issues[0].stage == "metadata_template"
    assert result.report.issues[0].path == "document_metadata.classification"
    assert result.report.issues[0].error_code == "metadata_required_missing"


def test_wrong_type_is_localized_and_value_is_not_emitted() -> None:
    result = _render(
        _template({"field_id": "retention_years", "type": "integer"}),
        metadata={"retention_years": "seven"},
    )

    assert result.passed is False
    assert result.document_metadata == {}
    issue = result.report.issues[0]
    assert issue.stage == "metadata_template"
    assert issue.path == "document_metadata.retention_years"
    assert issue.error_code == "metadata_type_mismatch"
    assert issue.expected_type == "integer"
    assert issue.actual_type == "string"


def test_empty_value_is_rejected_when_allow_empty_is_false() -> None:
    result = _render(
        _template(
            {
                "field_id": "department",
                "type": "string",
                "allow_empty": False,
            }
        ),
        metadata={"department": ""},
    )

    assert result.passed is False
    assert result.report.issues[0].error_code == "metadata_empty_not_allowed"


def test_optional_legacy_null_default_remains_deterministic() -> None:
    result = _render(
        _template({"field_id": "source", "required": False, "default": None})
    )

    assert result.passed is True
    assert result.document_metadata == {"source": None}
    assert result.report.field_traces[0].source.kind == "default"


def test_two_templates_change_document_metadata_for_the_same_uir() -> None:
    chinese = _render(
        _template({"field_id": "language", "type": "string", "default": "zh-CN"})
    )
    english = _render(
        _template({"field_id": "language", "type": "string", "default": "en-US"})
    )

    assert chinese.document_metadata != english.document_metadata


def test_repeated_render_is_byte_for_byte_deterministic() -> None:
    template = _template(
        {"field_id": "language", "type": "string", "default": "zh-CN"},
        {"field_id": "doc_id", "type": "string", "source_path": "system.doc_id"},
    )

    first = _render(template).model_dump_json()
    second = _render(template).model_dump_json()

    assert first == second
