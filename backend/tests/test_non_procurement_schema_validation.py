from pathlib import Path

from app.services.schema_service import SchemaService

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "examples" / "production_like" / "schemas"


def test_non_procurement_core_required_fields_remain_required() -> None:
    service = SchemaService(SCHEMAS_DIR)

    assert {
        field.field_id
        for field in service.get_required_fields(service.load_schema("general_doc"))
    } == {"title", "content"}
    assert {
        field.field_id
        for field in service.get_required_fields(service.load_schema("meeting_doc"))
    } == {"meeting_title", "meeting_date", "content"}
    assert {
        field.field_id
        for field in service.get_required_fields(service.load_schema("policy_doc"))
    } == {"title", "issuer", "publish_date", "content"}


def test_procurement_required_fields_are_unchanged() -> None:
    service = SchemaService(SCHEMAS_DIR)
    required = {
        field.field_id
        for field in service.get_required_fields(service.load_schema("procurement_doc"))
    }

    assert {"title", "project_name", "purchaser"} <= required
