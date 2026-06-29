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
    "document_title",
    "notice_type",
    "project_name",
    "project_id",
    "buyer_name",
    "agency_name",
    "supplier_name",
    "budget_amount",
    "winning_amount",
    "currency",
    "procurement_method",
    "notice_date",
    "deadline",
    "contact_person",
    "contact_phone",
    "contact_address",
    "source_url",
    "source_site",
]


def test_schema_service_loads_procurement_schema_v1() -> None:
    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", version="1.0.0")

    assert schema.schema_id == "procurement_doc"
    assert schema.version == "1.0.0"
    assert [field.field_id for field in schema.fields] == EXPECTED_FIELD_IDS
    assert [field.field_id for field in schema.fields if field.required] == [
        "document_title",
        "notice_type",
        "project_name",
        "source_url",
        "source_site",
    ]
    assert next(field for field in schema.fields if field.field_id == "deadline").type == (
        "datetime"
    )
    assert schema.json_schema["required"] == [
        "document_title",
        "notice_type",
        "project_name",
        "source_url",
        "source_site",
    ]
    assert schema.json_schema["properties"]["budget_amount"]["type"] == "number"
    assert schema.json_schema["properties"]["winning_amount"]["type"] == "number"
    assert schema.json_schema["properties"]["notice_date"] == {
        "type": "string",
        "format": "date",
    }
    assert schema.json_schema["properties"]["deadline"] == {
        "type": "string",
        "format": "date-time",
    }
    assert schema.json_schema["properties"]["notice_type"]["enum"] == [
        "procurement_notice",
        "tender_notice",
        "award_notice",
        "correction_notice",
        "result_notice",
    ]
    assert schema.json_schema["properties"]["procurement_method"]["enum"] == [
        "open_tender",
        "competitive_consultation",
        "competitive_negotiation",
        "inquiry",
        "single_source",
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
        template.aliases["winning_amount"]
    )
    assert {"采购人", "采购单位", "招标人", "建设单位"} <= set(
        template.aliases["buyer_name"]
    )
    assert {"中标供应商", "成交供应商", "供应商名称", "中标人", "成交人"} <= set(
        template.aliases["supplier_name"]
    )
    assert {rule.target_field_id for rule in template.regex_rules} == {
        "project_id",
        "budget_amount",
        "winning_amount",
        "notice_date",
        "deadline",
    }
    assert template.defaults == {"currency": "CNY"}
    assert template.enum_maps["notice_type"] == {
        "采购公告": "procurement_notice",
        "招标公告": "tender_notice",
        "中标公告": "award_notice",
        "成交公告": "award_notice",
        "更正公告": "correction_notice",
        "结果公告": "result_notice",
    }
    assert template.enum_maps["procurement_method"] == {
        "公开招标": "open_tender",
        "竞争性磋商": "competitive_consultation",
        "竞争性谈判": "competitive_negotiation",
        "询价": "inquiry",
        "单一来源": "single_source",
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
