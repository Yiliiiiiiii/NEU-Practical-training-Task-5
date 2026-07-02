from pathlib import Path
from typing import Any

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"


def make_uir(
    blocks: list[dict[str, Any]], metadata: dict[str, Any] | None = None
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc_non_procurement",
            "metadata": metadata or {},
            "blocks": blocks,
            "assets": [],
            "normalization_records": [],
        }
    )


def extract(blocks: list[dict[str, Any]]):
    candidates = CandidateService().extract_candidates(
        "task_non_procurement", make_uir(blocks)
    )
    candidate_ids = [item.candidate_id for item in candidates]
    assert len(candidate_ids) == len(set(candidate_ids))
    return candidates


def candidate_by_name(candidates, source_name: str):
    return next(item for item in candidates if item.source_name == source_name)


def mapped_field(
    schema_id: str,
    template_id: str,
    block_text: str,
    target_field_id: str,
):
    uir = make_uir([{"block_id": "regex", "type": "paragraph", "text": block_text}])
    report = mapping_report(uir, schema_id, template_id)
    return next(
        item for item in report.mappings if item["target_field_id"] == target_field_id
    )


def mapping_report(uir: UIRDocument, schema_id: str, template_id: str):
    from app.services.mapping_service import MappingService
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    candidates = CandidateService().extract_candidates("task_regex_owner", uir)
    schema = SchemaService(PRODUCTION_LIKE_DIR / "schemas").load_schema(schema_id)
    template = TemplateService(
        PRODUCTION_LIKE_DIR / "mapping_templates"
    ).load_template(template_id)
    report = MappingService().map_fields(
        "task_regex_owner", uir, schema, template, candidates
    )
    return report


def test_all_template_regex_owned_labels_are_reserved_from_key_value_aliases():
    expected_by_domain = {
        "general_doc": {
            "创建日期",
            "形成日期",
            "发布日期",
            "公开日期",
            "联系电话",
            "联系方式",
            "咨询电话",
        },
        "meeting_doc": {"会议日期", "会议时间", "召开日期", "召开时间"},
        "policy_doc": {"发布日期", "发文日期", "印发日期", "成文日期", "摘要"},
        "contract_doc": {"合同金额", "总金额"},
        "procurement_doc": {
            "项目编号",
            "采购编号",
            "招标编号",
            "采购项目编号",
            "预算金额",
            "项目预算",
            "采购预算",
            "中标金额",
            "成交金额",
            "中标（成交）金额",
            "总中标金额",
            "公告日期",
            "公告时间",
            "发布时间",
            "发布日期",
            "投标截止时间",
            "提交投标文件截止时间",
            "响应文件提交截止时间",
            "开标时间",
            "开启时间",
            "开标日期",
        },
    }

    assert CandidateService.TEMPLATE_REGEX_OWNED_LABELS_BY_DOMAIN == expected_by_domain
    assert CandidateService.TEMPLATE_REGEX_OWNED_LABELS_FALLBACK == set().union(
        *expected_by_domain.values()
    )


def test_heading_and_heading_attributes_emit_traceable_title_candidates():
    candidates = extract(
        [
            {
                "block_id": "heading_level_2",
                "type": "heading",
                "level": 2,
                "text": "办理事项",
            },
            {
                "block_id": "heading_level_1",
                "type": "paragraph",
                "text": "城市更新实施指南",
                "attributes": {"heading_level": 1},
            },
        ]
    )

    headings = [item for item in candidates if item.source_name == "heading"]
    assert [item.value_sample for item in headings] == ["办理事项", "城市更新实施指南"]
    assert {item.source_name for item in candidates} >= {
        "document_title",
        "policy_title",
        "meeting_title",
        "guide_title",
    }
    for source_name in ("document_title", "policy_title", "meeting_title", "guide_title"):
        title = candidate_by_name(candidates, source_name)
        assert title.value_sample == "城市更新实施指南"
        assert title.source_path == "$.blocks.heading_level_1.text"
        assert title.source_blocks == ["heading_level_1"]
        assert title.confidence == 0.8
        assert title.evidence == ["extracted from heading"]


def test_conflicting_structured_title_prevents_synthetic_heading_title_aliases():
    uir = make_uir(
        [{"block_id": "title", "type": "heading", "level": 1, "text": "OCR识别标题"}],
        metadata={"domain": "general_doc", "title": "权威文档标题"},
    )

    candidates = CandidateService().extract_candidates("task_structured_title", uir)

    assert candidate_by_name(candidates, "title").value_sample == "权威文档标题"
    assert candidate_by_name(candidates, "heading").value_sample == "OCR识别标题"
    assert not any(
        item.source_name in CandidateService.TITLE_CANDIDATE_NAMES
        for item in candidates
    )
    report = mapping_report(uir, "general_doc", "general_doc_base_v1")
    title_mapping = next(
        item for item in report.mappings if item["target_field_id"] == "title"
    )
    assert title_mapping["source_field_name"] == "title"
    assert title_mapping["value_sample"] == "权威文档标题"


def test_key_value_title_prevents_synthetic_alias_and_keeps_mapping_precedence():
    uir = make_uir(
        [
            {
                "block_id": "structured_title",
                "type": "paragraph",
                "text": "会议名称：权威标题",
            },
            {
                "block_id": "heading",
                "type": "heading",
                "level": 1,
                "text": "会议议程",
            },
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_key_value_title", uir)

    assert candidate_by_name(candidates, "会议名称").value_sample == "权威标题"
    assert candidate_by_name(candidates, "heading").value_sample == "会议议程"
    assert not any(
        item.source_name in CandidateService.TITLE_CANDIDATE_NAMES
        for item in candidates
    )
    report = mapping_report(uir, "meeting_doc", "meeting_doc_base_v1")
    title_mapping = next(
        item for item in report.mappings if item["target_field_id"] == "meeting_title"
    )
    assert title_mapping["source_field_name"] == "会议名称"
    assert title_mapping["value_sample"] == "权威标题"


def test_h2_only_does_not_emit_synthetic_title_aliases():
    candidates = extract(
        [{"block_id": "h2", "type": "heading", "level": 2, "text": "办理条件"}]
    )

    assert candidate_by_name(candidates, "heading").value_sample == "办理条件"
    assert not any(
        item.source_name in CandidateService.TITLE_CANDIDATE_NAMES
        for item in candidates
    )


def test_title_block_with_explicit_level_two_does_not_emit_synthetic_aliases():
    candidates = extract(
        [{"block_id": "title_h2", "type": "title", "level": 2, "text": "二级标题"}]
    )

    assert candidate_by_name(candidates, "heading").value_sample == "二级标题"
    assert not any(
        item.source_name in CandidateService.TITLE_CANDIDATE_NAMES
        for item in candidates
    )


def test_title_block_without_level_emits_synthetic_aliases():
    candidates = extract(
        [{"block_id": "title", "type": "title", "text": "正式文档标题"}]
    )

    assert {
        item.source_name
        for item in candidates
        if item.source_name in CandidateService.TITLE_CANDIDATE_NAMES
    } == set(CandidateService.TITLE_CANDIDATE_NAMES)


def test_title_path_accepts_nonempty_list_and_string():
    candidates = extract(
        [
            {
                "block_id": "path_list",
                "type": "paragraph",
                "text": "第一项",
                "attributes": {"title_path": ["政务服务", "个人办事", "户籍"]},
            },
            {
                "block_id": "path_string",
                "type": "paragraph",
                "text": "第二项",
                "attributes": {"title_path": "政策文件 / 市级文件"},
            },
        ]
    )

    title_paths = [item for item in candidates if item.source_name == "title_path"]
    assert [item.value_sample for item in title_paths] == [
        "政务服务 > 个人办事 > 户籍",
        "政策文件 / 市级文件",
    ]
    assert [item.source_blocks for item in title_paths] == [["path_list"], ["path_string"]]
    assert all(item.evidence == ["extracted from title_path"] for item in title_paths)


def test_chinese_key_value_paragraphs_support_colons_and_list_prefixes():
    candidates = extract(
        [
            {"block_id": "kv_cn", "type": "paragraph", "text": "办理地点：市民中心三楼"},
            {
                "block_id": "kv_ascii",
                "type": "paragraph",
                "text": "联系地址: 市民中心",
            },
            {
                "block_id": "kv_prefix_cn",
                "type": "paragraph",
                "text": "（一）申请条件：具有本市户籍",
            },
            {
                "block_id": "kv_prefix_number",
                "type": "paragraph",
                "text": "2. 办理时限：5个工作日",
            },
            {"block_id": "noise", "type": "paragraph", "text": "备注：此处仅作说明"},
        ]
    )

    values = {
        item.source_name: item.value_sample
        for item in candidates
        if item.evidence == ["extracted from key_value"]
    }
    assert values == {
        "办理地点": "市民中心三楼",
        "联系地址": "市民中心",
        "申请条件": "具有本市户籍",
        "办理时限": "5个工作日",
    }
    key_value_candidates = [
        item for item in candidates if item.evidence == ["extracted from key_value"]
    ]
    assert all(item.source_blocks for item in key_value_candidates)
    assert all(item.source_path.endswith(".text") for item in key_value_candidates)
    assert all(item.confidence == 0.8 for item in key_value_candidates)


def test_recognized_heading_attaches_to_next_list_items():
    candidates = extract(
        [
            {"block_id": "materials_heading", "type": "heading", "text": "申请材料"},
            {
                "block_id": "materials_list",
                "type": "list",
                "attributes": {"items": ["身份证明", "申请表", "近期照片"]},
            },
        ]
    )

    materials = next(
        item
        for item in candidates
        if item.source_name == "申请材料"
        and item.evidence == ["extracted from list_item"]
    )
    assert materials.value_sample == "身份证明\n申请表\n近期照片"
    assert materials.source_path == "$.blocks.materials_list.attributes.items"
    assert materials.source_blocks == ["materials_heading", "materials_list"]
    assert materials.confidence == 0.8


def test_intervening_meaningful_block_breaks_headed_list_adjacency():
    candidates = extract(
        [
            {"block_id": "heading", "type": "heading", "text": "申请材料"},
            {"block_id": "paragraph", "type": "paragraph", "text": "请先阅读办理须知。"},
            {
                "block_id": "list",
                "type": "list",
                "attributes": {"items": ["身份证明", "申请表"]},
            },
        ]
    )

    assert not any(
        item.source_name == "申请材料"
        and item.evidence == ["extracted from list_item"]
        for item in candidates
    )


def test_paragraph_regex_extracts_document_number_meeting_date_phone_and_issuer():
    candidates = extract(
        [
            {
                "block_id": "doc_number",
                "type": "paragraph",
                "text": "发文字号：城政办〔2026〕18号",
            },
            {
                "block_id": "meeting_date",
                "type": "paragraph",
                "text": "会议时间：2026年7月2日 09:30",
            },
            {
                "block_id": "phone",
                "type": "paragraph",
                "text": "咨询电话：010-12345678",
            },
            {
                "block_id": "issuer",
                "type": "paragraph",
                "text": "发布机关：城市管理委员会",
            },
        ]
    )

    expected = {
        "paragraph_regex.document_number": (
            "document_number",
            "城政办〔2026〕18号",
            "doc_number",
        ),
        "paragraph_regex.meeting_date": (
            "meeting_date",
            "2026年7月2日",
            "meeting_date",
        ),
        "paragraph_regex.contact": ("contact_phone", "010-12345678", "phone"),
        "paragraph_regex.issuer": ("issuer", "城市管理委员会", "issuer"),
    }
    for source_name, (display_name, value, block_id) in expected.items():
        item = candidate_by_name(candidates, source_name)
        assert item.display_name == display_name
        assert item.value_sample == value
        assert item.source_path == f"$.blocks.{block_id}.text"
        assert item.source_blocks == [block_id]
        assert item.confidence <= 0.72
        assert item.evidence == ["extracted from paragraph_regex"]


def test_unlabeled_full_date_is_generic_low_confidence_evidence():
    candidates = extract(
        [{"block_id": "date", "type": "paragraph", "text": "本通知自2026年8月1日起施行。"}]
    )

    date = candidate_by_name(candidates, "paragraph_regex.date")
    assert date.display_name == "date"
    assert date.value_sample == "2026年8月1日"
    assert date.confidence < 0.7
    assert date.source_blocks == ["date"]
    assert date.evidence == ["extracted from paragraph_regex"]
    assert not any(
        item.source_name in {"publish_date", "effective_date"} for item in candidates
    )


def test_empty_malformed_blocks_do_not_crash_or_duplicate_heading_candidates():
    candidates = extract(
        [
            {"block_id": "empty", "type": "paragraph", "text": None},
            {
                "block_id": "bad_list",
                "type": "list",
                "attributes": {"items": {"not": "a list"}},
            },
            {
                "block_id": "bad_path",
                "type": "paragraph",
                "attributes": {"title_path": {"not": "a path"}},
            },
            {
                "block_id": "multi_heading_signal",
                "type": "title",
                "level": 1,
                "text": "办事指南",
                "attributes": {"heading_level": 1},
            },
        ]
    )

    matching_headings = [
        item
        for item in candidates
        if item.source_name == "heading"
        and item.value_sample == "办事指南"
        and item.source_blocks == ["multi_heading_signal"]
    ]
    assert len(matching_headings) == 1
    assert all(item.value_sample not in (None, "") for item in candidates)


def test_candidate_ids_are_unique_when_source_names_sanitize_to_same_base():
    uir = make_uir(
        [{"block_id": "date", "type": "paragraph", "text": "2026年7月2日"}],
        metadata={"paragraph_regex_date": "metadata value"},
    )

    candidates = CandidateService().extract_candidates("task_id_collision", uir)
    colliding = [
        item
        for item in candidates
        if item.source_name in {"paragraph_regex_date", "paragraph_regex.date"}
    ]
    candidate_ids = [item.candidate_id for item in candidates]

    assert len(colliding) == 2
    assert len(candidate_ids) == len(set(candidate_ids))
    assert {item.candidate_id.rsplit("_", 1)[-1] for item in colliding} == {"1", "2"}


def test_publication_and_effective_date_text_remains_reviewable_candidate_evidence():
    candidates = extract(
        [
            {
                "block_id": "badcase_like",
                "type": "paragraph",
                "text": "发布日期：2026年6月1日，有效期至2027年6月1日。",
            }
        ]
    )

    date_candidates = [
        item
        for item in candidates
        if item.value_sample in {"2026年6月1日", "2027年6月1日"}
    ]
    assert date_candidates
    assert all(item.confidence <= 0.72 for item in date_candidates)
    assert all(item.source_name.startswith("paragraph_regex.") for item in date_candidates)
    assert not any(
        item.source_name in {"publish_date", "effective_date"} for item in candidates
    )


def test_template_owned_labels_use_namespaced_evidence_not_key_value_aliases():
    candidates = extract(
        [
            {
                "block_id": "summary",
                "type": "paragraph",
                "text": "摘要：用于验证模板正则优先级",
            },
            {
                "block_id": "publish_date",
                "type": "paragraph",
                "text": "发布日期：2026年7月2日",
            },
        ]
    )

    assert not any(item.source_name in {"摘要", "发布日期"} for item in candidates)
    publish_date = candidate_by_name(candidates, "paragraph_regex.date")
    assert not any(item.source_name == "paragraph_regex.summary" for item in candidates)
    assert publish_date.display_name == "date"
    assert publish_date.value_sample == "2026年7月2日"
    assert publish_date.source_blocks == ["publish_date"]
    assert publish_date.confidence <= 0.72
    assert publish_date.evidence == ["extracted from paragraph_regex"]
    summary_mapping = mapped_field(
        "policy_doc", "policy_doc_base_v1", "摘要：用于验证模板正则优先级", "summary"
    )
    assert summary_mapping["method"] == "regex"


def test_regex_owned_labels_are_reserved_only_for_the_active_domain():
    general_summary = CandidateService().extract_candidates(
        "task_general_summary",
        make_uir(
            [{"block_id": "summary", "type": "paragraph", "text": "摘要：通用摘要"}],
            metadata={"domain": "general_doc"},
        ),
    )
    policy_summary = CandidateService().extract_candidates(
        "task_policy_summary",
        make_uir(
            [{"block_id": "summary", "type": "paragraph", "text": "摘要：政策摘要"}],
            metadata={"domain": "policy_doc"},
        ),
    )
    general_publish_time = CandidateService().extract_candidates(
        "task_general_publish_time",
        make_uir(
            [
                {
                    "block_id": "publish_time",
                    "type": "paragraph",
                    "text": "发布时间：2026年7月2日",
                }
            ],
            metadata={"domain": "general_doc"},
        ),
    )
    procurement_publish_time = CandidateService().extract_candidates(
        "task_procurement_publish_time",
        make_uir(
            [
                {
                    "block_id": "publish_time",
                    "type": "paragraph",
                    "text": "发布时间：2026年7月2日",
                }
            ],
            metadata={"domain": "procurement_doc"},
        ),
    )

    assert candidate_by_name(general_summary, "摘要").value_sample == "通用摘要"
    assert not any(item.source_name == "摘要" for item in policy_summary)
    assert candidate_by_name(general_publish_time, "发布时间").value_sample == "2026年7月2日"
    assert not any(item.source_name == "发布时间" for item in procurement_publish_time)


def test_malformed_domain_values_use_conservative_fallback_without_crashing():
    for domain in (["general_doc"], {"name": "general_doc"}):
        candidates = CandidateService().extract_candidates(
            "task_malformed_domain",
            make_uir(
                [{"block_id": "summary", "type": "paragraph", "text": "摘要：保留内容"}],
                metadata={"domain": domain},
            ),
        )

        assert not any(item.source_name == "摘要" for item in candidates)


def test_standalone_phone_label_preserves_general_template_regex_strategy():
    mapping = mapped_field(
        "general_doc",
        "general_doc_base_v1",
        "联系电话：010-12345678",
        "contact",
    )

    assert mapping["method"] == "regex"


def test_contract_amount_label_preserves_contract_template_regex_strategy():
    mapping = mapped_field(
        "contract_doc",
        "contract_doc_base_v1",
        "合同金额：123456元",
        "amount",
    )

    assert mapping["method"] == "regex"


def test_procurement_id_label_preserves_procurement_template_regex_strategy():
    mapping = mapped_field(
        "procurement_doc",
        "procurement_doc_base_v1",
        "项目编号：CG-2026-01",
        "procurement_id",
    )

    assert mapping["method"] == "regex"


def test_legacy_candidate_evidence_remains_byte_for_byte_compatible():
    uir = make_uir(
        [
            {
                "block_id": "table",
                "type": "table",
                "attributes": {"rows": [{"field": "办理单位", "value": "市政务中心"}]},
            }
        ],
        metadata={"title": "办事指南"},
    )

    candidates = CandidateService().extract_candidates("task_legacy_evidence", uir)
    metadata = candidate_by_name(candidates, "title")
    table = candidate_by_name(candidates, "办理单位")

    assert metadata.evidence == ["extracted from metadata"]
    assert table.evidence == ["extracted from table"]


def test_new_candidate_samples_and_regex_matches_are_bounded():
    oversized = "超" * 1200
    dates = " ".join(f"2026年1月{day}日" for day in range(1, 21))
    candidates = extract(
        [
            {"block_id": "heading", "type": "heading", "level": 1, "text": oversized},
            {
                "block_id": "title_path",
                "type": "paragraph",
                "attributes": {"title_path": oversized},
            },
            {"block_id": "materials_heading", "type": "heading", "text": "申请材料"},
            {
                "block_id": "materials",
                "type": "list",
                "attributes": {"items": [oversized, oversized]},
            },
            {"block_id": "dates", "type": "paragraph", "text": dates},
        ]
    )

    heading = candidate_by_name(candidates, "heading")
    title_path = candidate_by_name(candidates, "title_path")
    materials = next(
        item
        for item in candidates
        if item.source_name == "申请材料"
        and item.evidence == ["extracted from list_item"]
    )
    date_candidates = [
        item for item in candidates if item.source_name == "paragraph_regex.date"
    ]

    assert len(heading.value_sample) == 1000
    assert len(title_path.value_sample) == 1000
    assert len(materials.value_sample) == 1000
    assert len(date_candidates) == 10
