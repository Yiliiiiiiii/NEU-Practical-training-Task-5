import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"


def test_schema_service_loads_production_like_schemas():
    from app.services.schema_service import SchemaService

    service = SchemaService(SCHEMAS_DIR)

    schemas = service.list_schemas()
    assert {schema.schema_id for schema in schemas} == {
        "policy_doc",
        "contract_doc",
        "meeting_doc",
        "general_doc",
        "procurement_doc",
    }

    policy_schema = service.load_schema("policy_doc", version="1.0.0")
    assert policy_schema.schema_id == "policy_doc"
    assert service.get_field(policy_schema, "issuer").display_name == "发布主体"
    assert service.get_field(policy_schema, "发布日期").field_id == "publish_date"


def test_schema_service_reports_required_fields():
    from app.services.schema_service import SchemaService

    service = SchemaService(SCHEMAS_DIR)
    policy_schema = service.load_schema("policy_doc")

    assert [field.field_id for field in service.get_required_fields(policy_schema)] == [
        "title",
        "issuer",
        "publish_date",
        "content",
    ]


def test_schema_service_rejects_duplicate_field_names(tmp_path):
    from app.services.schema_service import SchemaService

    schema = json.loads((SCHEMAS_DIR / "general_doc_v1.json").read_text(encoding="utf-8"))
    schema["fields"][1]["name"] = schema["fields"][0]["name"]
    schema_path = tmp_path / "duplicate_schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

    service = SchemaService(tmp_path)

    with pytest.raises(ValueError, match="duplicate field name"):
        service.load_schema("general_doc")


def test_schema_service_rejects_invalid_field_type(tmp_path):
    from app.services.schema_service import SchemaService

    schema = json.loads((SCHEMAS_DIR / "general_doc_v1.json").read_text(encoding="utf-8"))
    schema["fields"][0]["type"] = "spreadsheet"
    schema_path = tmp_path / "invalid_type_schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

    service = SchemaService(tmp_path)

    with pytest.raises(ValueError, match="unsupported field type"):
        service.load_schema("general_doc")


def test_template_service_loads_production_like_templates():
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    schema_service = SchemaService(SCHEMAS_DIR)
    template_service = TemplateService(TEMPLATES_DIR)
    policy_schema = schema_service.load_schema("policy_doc")

    templates = template_service.list_templates()
    assert {template.template_id for template in templates} == {
        "policy_doc_base_v1",
        "contract_doc_base_v1",
        "meeting_doc_base_v1",
        "general_doc_base_v1",
        "procurement_doc_base_v1",
    }

    template = template_service.load_template("policy_doc_base_v1", version="1.0.0")
    template_service.validate_template(template, policy_schema)
    assert template.schema_id == "policy_doc"
    assert "标题" in template.aliases["title"]


def test_template_service_rejects_unknown_alias_target(tmp_path):
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    schema = SchemaService(SCHEMAS_DIR).load_schema("policy_doc")
    template = json.loads(
        (TEMPLATES_DIR / "policy_doc_base_v1.json").read_text(encoding="utf-8")
    )
    template["aliases"]["unknown_field"] = ["未知字段"]
    (tmp_path / "bad_template.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )

    service = TemplateService(tmp_path)

    with pytest.raises(ValueError, match="unknown alias target"):
        service.validate_template(service.load_template("policy_doc_base_v1"), schema)


def test_template_service_rejects_unknown_regex_target(tmp_path):
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    schema = SchemaService(SCHEMAS_DIR).load_schema("policy_doc")
    template = json.loads(
        (TEMPLATES_DIR / "policy_doc_base_v1.json").read_text(encoding="utf-8")
    )
    template["regex_rules"][0]["target_field_id"] = "unknown_field"
    (tmp_path / "bad_template.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )

    service = TemplateService(tmp_path)

    with pytest.raises(ValueError, match="unknown regex target"):
        service.validate_template(service.load_template("policy_doc_base_v1"), schema)


def test_template_service_rejects_unknown_transform_target(tmp_path):
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    schema = SchemaService(SCHEMAS_DIR).load_schema("policy_doc")
    template = json.loads(
        (TEMPLATES_DIR / "policy_doc_base_v1.json").read_text(encoding="utf-8")
    )
    template["transform_rules"][0]["target_field_id"] = "unknown_field"
    (tmp_path / "bad_template.json").write_text(
        json.dumps(template, ensure_ascii=False),
        encoding="utf-8",
    )

    service = TemplateService(tmp_path)

    with pytest.raises(ValueError, match="unknown transform target"):
        service.validate_template(service.load_template("policy_doc_base_v1"), schema)
