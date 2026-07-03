import re
from pathlib import Path

import pytest

from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"

TEMPLATES = {
    "general_doc": "general_doc_base_v1",
    "meeting_doc": "meeting_doc_base_v1",
    "policy_doc": "policy_doc_base_v1",
}

EXPECTED_ALIASES = {
    "general_doc": {
        "title": {
            "document_title",
            "guide_title",
            "事项名称",
            "服务事项",
            "办事事项",
            "项目名称",
            "通知标题",
            "指南名称",
            "业务名称",
        },
        "issuer": {
            "发布机构",
        },
        "published_at": {"发布时间", "印发日期"},
        "service_object": {
            "面向对象",
            "申请对象",
            "办理对象",
            "支持对象",
            "申报对象",
            "申报主体",
            "申报主体要求",
            "项目负责人要求",
        },
        "application_conditions": {"受理条件", "资格条件", "基本条件"},
        "application_materials": {"所需材料", "提交材料", "材料清单"},
        "process_steps": {
            "办理程序",
            "申请流程",
            "办事流程",
            "操作流程",
            "流程说明",
            "申报方式",
        },
        "contact": {"联系地址", "服务热线"},
    },
    "meeting_doc": {
        "meeting_title": {"会议纪要", "专题会议", "常务会议"},
        "attendees": {"参会同志", "出席同志", "参加人员"},
        "chairperson": {"主持", "会议主持"},
        "topics": {"会议议程", "研究事项", "讨论事项"},
        "decisions": {"会议要求", "工作部署"},
        "action_items": {"下一步工作", "任务分工"},
    },
    "policy_doc": {
        "title": {"policy_title", "文件名称", "政策标题", "文件标题"},
        "issuer": {"发文机关"},
        "document_number": {"政策编号", "通知编号"},
        "publish_date": {"发布时间", "公开日期"},
        "effective_date": {"施行日期", "执行日期"},
        "target_audience": {"适用范围", "支持对象", "申报主体", "面向对象"},
        "policy_measures": {"扶持措施", "重点任务", "工作措施", "具体措施"},
    },
}


def load_template(schema_id: str):
    return TemplateService(TEMPLATES_DIR).load_template(TEMPLATES[schema_id], "1.0.0")


def load_schema(schema_id: str) -> TargetSchema:
    return SchemaService(SCHEMAS_DIR).load_schema(schema_id, "1.0.0")


def map_metadata_doc(schema_id: str, metadata: dict[str, str]):
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": f"{schema_id}_semantic_alias_probe",
            "metadata": metadata,
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )
    task_id = f"task_{schema_id}_semantic_alias_probe"
    schema = load_schema(schema_id)
    template = load_template(schema_id)
    candidates = CandidateService().extract_candidates(task_id, uir)
    return MappingService().map_fields(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )


def mapping_for_source(report, source_field_name: str):
    return next(
        (
            item
            for item in [*report.mappings, *report.review_required_items]
            if item["source_field_name"] == source_field_name
        ),
        None,
    )


def effective_alias_owners(schema: TargetSchema, template: MappingTemplate) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for field in schema.fields:
        aliases = set(template.aliases.get(field.field_id, []))
        aliases.update(field.aliases)
        aliases.add(field.display_name)
        for alias in aliases:
            normalized = MappingService.normalize_name(alias)
            owners.setdefault(normalized, set()).add(field.field_id)
    return owners


@pytest.mark.parametrize("schema_id", TEMPLATES)
def test_high_frequency_aliases_are_available_without_invalid_targets(schema_id: str) -> None:
    schema_service = SchemaService(SCHEMAS_DIR)
    schema = schema_service.load_schema(schema_id, "1.0.0")
    template = load_template(schema_id)
    field_ids = {field.field_id for field in schema.fields}

    for target_field_id, expected_aliases in EXPECTED_ALIASES[schema_id].items():
        assert expected_aliases <= set(template.aliases[target_field_id])

    assert set(template.aliases) <= field_ids
    assert {rule.target_field_id for rule in template.regex_rules} <= field_ids
    assert TemplateService(TEMPLATES_DIR).validate_template(template, schema) is template


def test_non_procurement_templates_map_traceable_source_urls() -> None:
    for schema_id in TEMPLATES:
        assert "source_url" in load_template(schema_id).aliases["source"]


def test_policy_template_excludes_ambiguous_issuer_and_authored_date_aliases() -> None:
    schema = load_schema("policy_doc")
    template = load_template("policy_doc")
    publish_field = next(field for field in schema.fields if field.field_id == "publish_date")

    assert "发布机构" not in template.aliases["issuer"]
    assert "成文日期" not in template.aliases["publish_date"]
    assert "成文日期" not in publish_field.aliases
    publish_rule = next(
        rule for rule in template.regex_rules if rule.target_field_id == "publish_date"
    )
    assert "成文日期" not in publish_rule.pattern


@pytest.mark.parametrize("schema_id", TEMPLATES)
def test_effective_aliases_do_not_collide_across_targets(schema_id: str) -> None:
    schema = load_schema(schema_id)
    template = load_template(schema_id)
    collisions = {
        alias: sorted(field_ids)
        for alias, field_ids in effective_alias_owners(schema, template).items()
        if len(field_ids) > 1
    }

    assert collisions == {}


def test_template_validation_rejects_effective_alias_collisions() -> None:
    schema = load_schema("policy_doc")
    template = load_template("policy_doc").model_copy(deep=True)
    template.aliases["title"] = [*template.aliases["title"], "发文机关"]

    with pytest.raises(ValueError, match="effective alias collision.*发文机关"):
        TemplateService(TEMPLATES_DIR).validate_template(template, schema)


@pytest.mark.parametrize("schema_id", TEMPLATES)
def test_alias_lists_are_duplicate_free_and_regex_rules_compile(schema_id: str) -> None:
    template = load_template(schema_id)

    for aliases in template.aliases.values():
        assert len(aliases) == len(set(aliases))
    for rule in template.regex_rules:
        re.compile(rule.pattern)
        assert isinstance(rule.group, int)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("文号：京政办发〔2026〕12号", "京政办发〔2026〕12号"),
        ("通知编号：沪府规[2025]8号", "沪府规[2025]8号"),
    ],
)
def test_policy_document_number_regex_extracts_explicit_number(
    text: str,
    expected: str,
) -> None:
    template = load_template("policy_doc")
    rule = next(
        rule for rule in template.regex_rules if rule.target_field_id == "document_number"
    )

    match = re.search(rule.pattern, text)

    assert rule.group == 1
    assert match is not None
    assert match.group(rule.group) == expected


@pytest.mark.parametrize("verb", ["施行", "实施", "执行"])
def test_policy_effective_date_regex_extracts_only_explicit_calendar_date(verb: str) -> None:
    template = load_template("policy_doc")
    rule = next(rule for rule in template.regex_rules if rule.target_field_id == "effective_date")

    match = re.search(rule.pattern, f"本办法自2026年7月1日起{verb}。")

    assert rule.group == 1
    assert match is not None
    assert match.group(rule.group) == "2026年7月1日"


@pytest.mark.parametrize(
    "text",
    [
        "本办法自发布之日起施行。",
        "本通知从印发之日起执行。",
        "发布日期：2026年7月1日",
    ],
)
def test_policy_effective_date_regex_rejects_relative_or_publish_dates(text: str) -> None:
    template = load_template("policy_doc")
    rule = next(rule for rule in template.regex_rules if rule.target_field_id == "effective_date")

    assert re.search(rule.pattern, text) is None


def test_unsafe_aliases_remain_excluded() -> None:
    general = load_template("general_doc")
    meeting = load_template("meeting_doc")
    policy = load_template("policy_doc")

    assert "联系人" not in general.aliases["contact"]
    assert "发布日期" not in policy.aliases["effective_date"]
    assert "主持人" not in meeting.aliases["attendees"]
    # Existing governance keeps ambiguous conveners review-required.
    assert "召集人" not in meeting.aliases["chairperson"]
    # Existing knowledge-pack governance learns this source label through review.
    assert "通知名称" not in policy.aliases["title"]
    assert "承办单位" not in general.aliases["issuer"]
    assert "承办单位" not in policy.aliases["issuer"]
    for template in (general, meeting, policy):
        assert "award_amount" not in template.aliases
        assert all(
            alias not in {"预算金额", "控制价"}
            for aliases in template.aliases.values()
            for alias in aliases
        )


@pytest.mark.parametrize(
    ("schema_id", "source_field_name", "forbidden_target_field_id"),
    [
        ("general_doc", "联系人", "contact"),
        ("general_doc", "责任单位", "issuer"),
        ("general_doc", "牵头单位", "issuer"),
        ("policy_doc", "责任部门", "issuer"),
        ("policy_doc", "牵头部门", "issuer"),
        ("meeting_doc", "列席人员", "attendees"),
    ],
)
def test_risky_role_labels_are_not_accepted_as_unrelated_targets(
    schema_id: str,
    source_field_name: str,
    forbidden_target_field_id: str,
) -> None:
    report = map_metadata_doc(
        schema_id,
        {
            source_field_name: (
                "张三" if source_field_name in {"联系人", "列席人员"} else "业务一处"
            ),
            "content": "正文内容。",
        },
    )
    accepted_forbidden = [
        item
        for item in report.mappings
        if item["source_field_name"] == source_field_name
        and item["target_field_id"] == forbidden_target_field_id
    ]

    assert accepted_forbidden == []


def test_meeting_participating_unit_maps_to_departments_not_attendees() -> None:
    report = map_metadata_doc(
        "meeting_doc",
        {
            "参会单位": "市发改委、市财政局",
            "content": "会议正文。",
        },
    )
    mapping = mapping_for_source(report, "参会单位")

    assert mapping is not None
    assert mapping["target_field_id"] == "departments"
    assert mapping["status"] == "accepted"


@pytest.mark.parametrize(
    "text",
    [
        "文号：京政办发〔2026]12号",
        "文号：京政办发[2026〕12号",
        "正文随意提到京政办发〔2026〕12号但没有标签",
    ],
)
def test_policy_document_number_regex_rejects_malformed_or_unlabeled_numbers(
    text: str,
) -> None:
    template = load_template("policy_doc")
    rule = next(
        rule for rule in template.regex_rules if rule.target_field_id == "document_number"
    )

    assert re.search(rule.pattern, text) is None


def test_badcase_blocks_new_alias_from_automatic_acceptance() -> None:
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "general_badcase_alias",
            "metadata": {
                "服务事项": "企业帮扶",
                "content": "办事指南正文。",
            },
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )
    schema = SchemaService(SCHEMAS_DIR).load_schema("general_doc", "1.0.0")
    template = load_template("general_doc")
    candidates = CandidateService().extract_candidates("task_badcase_alias", uir)

    report = MappingService().map_fields(
        task_id="task_badcase_alias",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={
            "badcases": [
                {
                    "source_field": "服务事项",
                    "forbidden_target_fields": ["title"],
                }
            ]
        },
    )

    assert not any(
        item["source_field_name"] == "服务事项" and item["target_field_id"] == "title"
        for item in report.mappings
    )
    blocked = next(
        item
        for item in report.review_required_items
        if item["source_field_name"] == "服务事项" and item["target_field_id"] == "title"
    )
    assert blocked["method"] == "alias"
    assert blocked["badcase_filter"]["blocked"] is True
    assert "badcase_blocked" in blocked["risk_flags"]
