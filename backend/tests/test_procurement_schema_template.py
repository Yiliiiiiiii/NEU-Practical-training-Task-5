from pathlib import Path

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

EXPECTED_FIELD_IDS = [
    "title",
    "project_name",
    "procurement_id",
    "procurement_type",
    "purchaser",
    "agency",
    "budget_amount",
    "award_supplier",
    "award_amount",
    "announcement_date",
    "bid_deadline",
    "opening_date",
    "contact_person",
    "contact_phone",
    "source_url",
    "source_site",
    "summary",
    "content",
]


def test_schema_service_loads_procurement_schema_v1() -> None:
    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", version="1.0.0")

    assert schema.schema_id == "procurement_doc"
    assert schema.version == "1.0.0"
    assert [field.field_id for field in schema.fields] == EXPECTED_FIELD_IDS
    assert [field.field_id for field in schema.fields if field.required] == [
        "title",
        "project_name",
        "purchaser",
    ]
    assert next(field for field in schema.fields if field.field_id == "bid_deadline").type == (
        "date"
    )
    assert schema.json_schema["required"] == [
        "title",
        "project_name",
        "purchaser",
    ]
    assert schema.json_schema["properties"]["budget_amount"]["type"] == "number"
    assert schema.json_schema["properties"]["award_amount"]["type"] == "number"
    assert schema.json_schema["properties"]["announcement_date"] == {
        "type": "string",
        "format": "date",
    }
    assert schema.json_schema["properties"]["bid_deadline"] == {
        "type": "string",
        "format": "date",
    }
    assert schema.json_schema["properties"]["procurement_type"]["enum"] == [
        "public_tender",
        "competitive_negotiation",
        "competitive_consultation",
        "inquiry",
        "single_source",
        "award",
        "other",
    ]


def test_template_service_loads_and_validates_procurement_template_v1() -> None:
    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", version="1.0.0")
    service = TemplateService(TEMPLATES_DIR)

    template = service.load_template("procurement_doc_base_v1", version="1.0.0")

    assert service.validate_template(template, schema) is template
    assert template.schema_id == "procurement_doc"
    assert template.version == "1.0.0"
    assert set(template.aliases) <= set(EXPECTED_FIELD_IDS)
    assert {rule.target_field_id for rule in template.regex_rules} <= set(EXPECTED_FIELD_IDS)
    assert set(template.defaults) <= set(EXPECTED_FIELD_IDS)
    assert set(template.enum_maps) <= set(EXPECTED_FIELD_IDS)
    assert {
        target
        for rule in template.transform_rules
        for target in ([rule.target_field_id] if rule.target_field_id else rule.target_fields)
    } <= set(EXPECTED_FIELD_IDS)
    assert {"项目名称", "采购项目名称", "工程名称", "标项名称"} <= set(
        template.aliases["project_name"]
    )
    assert {"预算金额", "项目预算", "采购预算", "最高限价", "预算价"} <= set(
        template.aliases["budget_amount"]
    )
    assert {"中标金额", "成交金额", "成交价", "中标价", "合同金额"} <= set(
        template.aliases["award_amount"]
    )
    assert {"采购人", "采购单位", "招标人", "建设单位"} <= set(
        template.aliases["purchaser"]
    )
    assert {"中标供应商", "成交供应商", "供应商名称", "中标人", "成交人"} <= set(
        template.aliases["award_supplier"]
    )
    assert {rule.target_field_id for rule in template.regex_rules} == {
        "procurement_id",
        "budget_amount",
        "award_amount",
        "announcement_date",
        "bid_deadline",
        "opening_date",
    }
    assert template.defaults == {}
    assert template.enum_maps["procurement_type"] == {
        "公开招标": "public_tender",
        "竞争性谈判": "competitive_negotiation",
        "竞争性磋商": "competitive_consultation",
        "询价": "inquiry",
        "单一来源": "single_source",
        "中标公告": "award",
        "成交公告": "award",
    }


def test_catalog_governance_seed_discovers_procurement_catalog() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        service = CatalogGovernanceService(
            session,
            schema_service=SchemaService(SCHEMAS_DIR),
            template_service=TemplateService(TEMPLATES_DIR),
        )

        service.seed_from_files()

        assert service.load_schema("procurement_doc", "1.0.0").schema_id == "procurement_doc"
        assert (
            service.load_template("procurement_doc_base_v1", "1.0.0").schema_id
            == "procurement_doc"
        )
