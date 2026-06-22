import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "examples" / "demo"


def load_json(name: str) -> dict:
    path = DEMO_DIR / name
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_demo_examples_exist_and_parse():
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema
    from app.schemas.uir import UIRDocument

    expected_files = [
        "example_uir_general_doc.json",
        "example_uir_policy_doc.json",
        "target_schema_general.json",
        "target_schema_policy.json",
        "mapping_template_general.json",
        "mapping_template_policy.json",
    ]

    for file_name in expected_files:
        assert (DEMO_DIR / file_name).is_file()

    general_uir = UIRDocument.model_validate(load_json("example_uir_general_doc.json"))
    policy_uir = UIRDocument.model_validate(load_json("example_uir_policy_doc.json"))
    general_schema = TargetSchema.model_validate(load_json("target_schema_general.json"))
    policy_schema = TargetSchema.model_validate(load_json("target_schema_policy.json"))
    general_template = MappingTemplate.model_validate(load_json("mapping_template_general.json"))
    policy_template = MappingTemplate.model_validate(load_json("mapping_template_policy.json"))

    assert general_uir.doc_id == "doc_demo_general_001"
    assert policy_uir.doc_id == "doc_demo_policy_001"
    assert {field.field_id for field in general_schema.fields} >= {
        "title",
        "author",
        "created_date",
        "language",
        "summary",
    }
    assert {field.field_id for field in policy_schema.fields} >= {
        "title",
        "publish_org",
        "publish_date",
        "doc_no",
        "doc_type",
        "main_content",
    }
    assert general_template.defaults["language"] == "zh-CN"
    assert policy_template.regex_rules[0].target_field_id == "publish_date"
    assert policy_template.enum_maps["doc_type"]["办法"] == "policy"


def test_demo_examples_cover_blocks_and_mapping_methods():
    general_uir = load_json("example_uir_general_doc.json")
    policy_uir = load_json("example_uir_policy_doc.json")
    general_template = load_json("mapping_template_general.json")
    policy_template = load_json("mapping_template_policy.json")

    assert len(general_uir["blocks"]) >= 6
    assert any(block["type"] == "list" for block in general_uir["blocks"])
    assert "文档标题" in general_template["aliases"]["title"]
    assert "created_date" in general_template["aliases"]
    assert any("发布日期" in block["text"] for block in policy_uir["blocks"])
    assert any(rule["operation"] == "date_format" for rule in policy_template["transform_rules"])
    assert any(rule["operation"] == "enum_map" for rule in policy_template["transform_rules"])
