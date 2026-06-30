from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.services.catalog_governance_service import CatalogGovernanceService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"

EXPECTED_FIELDS = {
    "general_doc": {
        "title",
        "source",
        "created_date",
        "category",
        "content",
        "tags",
        "document_subtype",
        "issuer",
        "published_at",
        "summary",
        "service_object",
        "application_conditions",
        "application_materials",
        "process_steps",
        "deadline",
        "contact",
        "attachments",
    },
    "meeting_doc": {
        "meeting_title",
        "meeting_date",
        "organizer",
        "attendees",
        "topics",
        "decisions",
        "action_items",
        "content",
        "meeting_number",
        "meeting_location",
        "chairperson",
        "departments",
        "agenda_items",
        "decision_items",
        "responsible_units",
        "deadlines",
        "source",
    },
    "policy_doc": {
        "title",
        "issuer",
        "publish_date",
        "doc_type",
        "effective_date",
        "summary",
        "keywords",
        "content",
        "document_number",
        "policy_level",
        "applicable_region",
        "target_audience",
        "policy_measures",
        "responsible_departments",
        "valid_until",
        "source",
    },
}

EXPECTED_REQUIRED = {
    "general_doc": {"title", "content"},
    "meeting_doc": {"meeting_title", "meeting_date", "content"},
    "policy_doc": {"title", "issuer", "publish_date", "content"},
}

TEMPLATE_IDS = {
    "general_doc": "general_doc_base_v1",
    "meeting_doc": "meeting_doc_base_v1",
    "policy_doc": "policy_doc_base_v1",
}


@pytest.mark.parametrize("schema_id", EXPECTED_FIELDS)
def test_non_procurement_schema_and_template_are_legal_and_minimally_required(
    schema_id: str,
) -> None:
    schema_service = SchemaService(SCHEMAS_DIR)
    template_service = TemplateService(TEMPLATES_DIR)

    schema = schema_service.load_schema(schema_id, "1.0.0")
    template = template_service.load_template(TEMPLATE_IDS[schema_id], "1.0.0")

    assert schema_service.validate_schema(schema) is schema
    assert template_service.validate_template(template, schema) is template

    field_ids = {field.field_id for field in schema.fields}
    required_by_fields = {field.field_id for field in schema.fields if field.required}
    assert EXPECTED_FIELDS[schema_id] <= field_ids
    assert required_by_fields == EXPECTED_REQUIRED[schema_id]
    assert set(schema.json_schema["required"]) == EXPECTED_REQUIRED[schema_id]
    assert set(schema.json_schema["properties"]) == field_ids
    assert set(template.aliases) <= field_ids
    assert {rule.target_field_id for rule in template.regex_rules} <= field_ids
    assert set(template.defaults) <= field_ids
    assert set(template.enum_maps) <= field_ids
    assert {
        target
        for rule in template.transform_rules
        for target in ([rule.target_field_id] if rule.target_field_id else rule.target_fields)
    } <= field_ids


def test_general_document_subtype_has_supported_enum_contract() -> None:
    schema = SchemaService(SCHEMAS_DIR).load_schema("general_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "general_doc_base_v1",
        "1.0.0",
    )

    subtype = next(field for field in schema.fields if field.field_id == "document_subtype")
    assert subtype.type == "enum"
    assert subtype.required is False
    assert subtype.constraints["enum"] == [
        "service_guide",
        "project_guide",
        "application_flow",
        "notice",
        "announcement",
        "manual",
        "other",
    ]
    assert schema.json_schema["properties"]["document_subtype"]["enum"] == (
        subtype.constraints["enum"]
    )
    assert template.enum_maps["document_subtype"] == {
        "办事指南": "service_guide",
        "项目指南": "project_guide",
        "申报流程": "application_flow",
        "通知": "notice",
        "公告": "announcement",
        "手册": "manual",
        "其他": "other",
    }


def test_catalog_governance_seeds_all_strengthened_non_procurement_catalogs() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        service = CatalogGovernanceService(
            session,
            schema_service=SchemaService(SCHEMAS_DIR),
            template_service=TemplateService(TEMPLATES_DIR),
        )
        service.seed_from_files()

        for schema_id, template_id in TEMPLATE_IDS.items():
            assert service.load_schema(schema_id, "1.0.0").schema_id == schema_id
            assert service.load_template(template_id, "1.0.0").schema_id == schema_id
