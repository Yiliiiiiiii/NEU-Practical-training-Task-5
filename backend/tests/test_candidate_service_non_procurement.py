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


def test_general_numbered_sections_emit_bounded_semantic_candidates() -> None:
    uir = make_uir(
        [
            {"block_id": "conditions", "type": "paragraph", "text": "二、申报要求"},
            {"block_id": "condition_body", "type": "paragraph", "text": "申请单位须诚信经营。"},
            {"block_id": "process", "type": "paragraph", "text": "三、申报方式"},
            {"block_id": "process_body", "type": "paragraph", "text": "通过管理系统网上填报。"},
            {"block_id": "review", "type": "paragraph", "text": "四、评审方式"},
        ],
        metadata={"domain": "general_doc"},
    )

    candidates = CandidateService().extract_candidates("task_sections", uir)

    conditions = candidate_by_name(candidates, "申报要求")
    assert conditions.value_sample == "申请单位须诚信经营。"
    assert conditions.source_blocks == ["conditions", "condition_body"]
    process = candidate_by_name(candidates, "申报方式")
    assert process.value_sample == "通过管理系统网上填报。"
    assert process.source_blocks == ["process", "process_body"]


def test_general_front_matter_guide_emits_generic_review_safe_candidates() -> None:
    uir = make_uir(
        [
            {"block_id": "title", "type": "heading", "level": 1, "text": "某市公共服务办事指南"},
            {"block_id": "subtitle", "type": "paragraph", "text": "某市公共服务办事指南"},
            {"block_id": "version", "type": "paragraph", "text": "（2026版）"},
            {"block_id": "items", "type": "paragraph", "text": "一、办理事项及证明材料清单"},
        ],
        metadata={"domain": "general_doc"},
    )

    candidates = CandidateService().extract_candidates("task_front_matter", uir)

    service = candidate_by_name(candidates, "service or subject section")
    assert service.display_name == "service_object"
    assert service.target_hints == ["service_object"]
    condition = candidate_by_name(candidates, "process or condition detail")
    assert condition.display_name == "application_conditions"
    category = candidate_by_name(candidates, "办理事项及证明材料清单")
    assert category.display_name == "category"
    assert "review_required" in category.quality_flags


def test_meeting_opening_sentence_emits_date_number_and_chairperson() -> None:
    uir = make_uir(
        [
            {
                "block_id": "opening",
                "type": "paragraph",
                "text": "202 6 年 1 月 7 日，县长马建国主持召开县人民政府2026年第1次常务会议。",
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_opening", uir)

    by_display_name = {item.display_name: item for item in candidates}
    assert by_display_name["meeting_date"].value_sample == "2026年1月7日"
    assert by_display_name["meeting_number"].value_sample == "第1次"
    assert by_display_name["chairperson"].value_sample == "马建国"


def test_government_meeting_opening_source_name_is_generic() -> None:
    uir = make_uir(
        [
            {
                "block_id": "opening",
                "type": "paragraph",
                "text": (
                    "2026年2月5日，县长李明主持召开"
                    "青河县第15届人民政府第23次常务会议，研究民生项目建设工作。"
                ),
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_generic_meeting", uir)

    meeting_date = next(
        item for item in candidates if item.display_name == "meeting_date"
    )
    assert meeting_date.source_name == "meeting sentence"


def test_policy_signature_and_official_page_url_emit_traceable_candidates() -> None:
    uir = make_uir(
        [
            {"block_id": "signature", "type": "paragraph", "text": "教 育 部"},
            {"block_id": "signed_date", "type": "paragraph", "text": "2025年1月3日"},
        ],
        metadata={
            "domain": "policy_doc",
            "source_url": "https://www.moe.gov.cn/srcsite/A29/202503/t20250326_1184786.html",
        },
    )

    candidates = CandidateService().extract_candidates("task_policy_signature", uir)

    issuer = candidate_by_name(candidates, "issuer")
    assert issuer.value_sample == "教育部"
    assert issuer.source_blocks == ["signature"]
    assert issuer.source_path == "$.blocks.signature.text"
    publish_date = next(
        item for item in candidates if item.display_name == "publish_date"
    )
    assert publish_date.value_sample == "2025-03-26"
    assert publish_date.source_blocks == []
    assert publish_date.source_path == "$.metadata.source_url#publish_date"


def test_policy_government_page_banner_emits_publication_date() -> None:
    uir = make_uir(
        [
            {
                "block_id": "page_banner",
                "type": "paragraph",
                "text": "中国政府网 2025-01-16",
            }
        ],
        metadata={"domain": "policy_doc", "source_url": "https://app.www.gov.cn/article.html"},
    )

    candidates = CandidateService().extract_candidates("task_policy_banner", uir)

    publish_date = next(
        item for item in candidates if item.display_name == "publish_date"
    )
    assert publish_date.value_sample == "2025-01-16"
    assert publish_date.source_blocks == ["page_banner"]
    assert publish_date.source_path == "$.blocks.page_banner.text#publish_date"


def test_policy_metadata_publish_date_uses_only_safe_publication_labels() -> None:
    uir = make_uir(
        [],
        metadata={
            "domain": "policy_doc",
            "发布日期": "2025-06-01",
            "成文日期": "2025-05-20",
        },
    )

    candidates = CandidateService().extract_candidates("task_policy_publish_metadata", uir)

    publish_date = candidate_by_name(candidates, "发布日期")
    assert publish_date.target_hints == ["publish_date"]
    assert publish_date.evidence_type == "metadata_publish_date"
    signed_date = candidate_by_name(candidates, "成文日期")
    assert "publish_date" not in signed_date.target_hints
    assert "forbidden_publish_date" in signed_date.quality_flags


def test_policy_metadata_effective_date_uses_only_safe_effective_labels() -> None:
    uir = make_uir(
        [],
        metadata={
            "domain": "policy_doc",
            "生效日期": "2025-07-01",
            "发布日期": "2025-06-01",
        },
    )

    candidates = CandidateService().extract_candidates("task_policy_effective_metadata", uir)

    effective_date = candidate_by_name(candidates, "生效日期")
    assert effective_date.target_hints == ["effective_date"]
    assert effective_date.evidence_type == "metadata_effective_date"
    publish_date = candidate_by_name(candidates, "发布日期")
    assert "effective_date" not in publish_date.target_hints


def test_policy_signature_date_is_not_treated_as_publication_date() -> None:
    uir = make_uir(
        [
            {"block_id": "signature", "type": "paragraph", "text": "财政部 教育部"},
            {"block_id": "signed_date", "type": "paragraph", "text": "2025年3月27日"},
        ],
        metadata={"domain": "policy_doc", "source_url": "https://example.gov.cn/document.pdf"},
    )

    candidates = CandidateService().extract_candidates("task_policy_signed_date", uir)

    assert candidate_by_name(candidates, "issuer").value_sample == "财政部、教育部"
    assert not any(item.source_name == "publish_date" for item in candidates)


def test_policy_url_path_date_requires_a_supported_official_site() -> None:
    uir = make_uir(
        [],
        metadata={
            "domain": "policy_doc",
            "source_url": "https://example.gov.cn/t20250326_123.html",
        },
    )

    candidates = CandidateService().extract_candidates("task_policy_url_date", uir)

    assert not any(item.source_name == "publish_date" for item in candidates)


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
        "城政办〔2026〕18号": (
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


def test_meeting_topics_candidates_are_traceable_and_exclude_noise_sections() -> None:
    uir = make_uir(
        [
            {"block_id": "agenda", "type": "heading", "level": 2, "text": "会议议题"},
            {
                "block_id": "agenda_item",
                "type": "paragraph",
                "text": "一、关于推进城市更新工作的事项",
            },
            {
                "block_id": "opening",
                "type": "paragraph",
                "text": "会议研究了生态环境治理工作。",
            },
            {"block_id": "requirements", "type": "heading", "level": 2, "text": "会议要求"},
            {
                "block_id": "requirement_body",
                "type": "paragraph",
                "text": "各部门抓好落实。",
            },
            {
                "block_id": "time",
                "type": "paragraph",
                "text": "会议时间：2025年6月1日",
            },
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_topics", uir)
    topics = [item for item in candidates if "topics" in item.target_hints]

    assert {item.evidence_type for item in topics} >= {
        "agenda_section",
        "meeting_opening_sentence",
    }
    assert any("关于推进城市更新工作" in str(item.value_sample) for item in topics)
    assert any("生态环境治理" in str(item.value_sample) for item in topics)
    assert all(item.source_path and item.source_blocks for item in topics)
    assert not any(
        "会议要求" in str(item.value_sample) or "会议时间" in str(item.value_sample)
        for item in topics
    )


def test_meeting_date_prefers_meeting_context_and_rejects_publication_context() -> None:
    uir = make_uir(
        [
            {
                "block_id": "publication",
                "type": "paragraph",
                "text": "发布日期：2025年5月30日",
            },
            {
                "block_id": "meeting",
                "type": "paragraph",
                "text": "2025年6月1日下午，会议听取了专项工作汇报。",
            },
        ],
        metadata={"domain": "meeting_doc", "retrieved_at": "2025-06-02T10:00:00Z"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_date_safe", uir)
    dates = [item for item in candidates if "meeting_date" in item.target_hints]

    assert dates
    assert dates[0].value_sample == "2025年6月1日"
    assert dates[0].source_blocks == ["meeting"]
    assert dates[0].confidence_hint <= 0.8
    assert not any(item.source_blocks == ["publication"] for item in dates)

    forbidden_only = CandidateService().extract_candidates(
        "task_meeting_date_forbidden",
        make_uir(
            [
                {
                    "block_id": "issue",
                    "type": "paragraph",
                    "text": "成文日期：2025年6月1日",
                }
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )
    assert not any("meeting_date" in item.target_hints for item in forbidden_only)


def test_meeting_number_supports_minutes_issue_patterns() -> None:
    uir = make_uir(
        [
            {
                "block_id": "number",
                "type": "paragraph",
                "text": "市政府会议纪要第12期",
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_number", uir)
    number = next(item for item in candidates if "meeting_number" in item.target_hints)

    assert number.value_sample == "第12期"
    assert number.source_blocks == ["number"]
    assert number.evidence_type == "meeting_number_pattern"


def test_meeting_number_supports_document_number_style_minutes() -> None:
    uir = make_uir(
        [
            {
                "block_id": "number",
                "type": "paragraph",
                "text": "汨政办发〔2026〕8号（关于废止相关文件的通知）",
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_doc_number", uir)
    number = next(item for item in candidates if "meeting_number" in item.target_hints)

    assert number.source_name == "汨政办发〔2026〕8号"
    assert number.value_sample == "汨政办发〔2026〕8号"
    assert number.source_blocks == ["number"]


def test_meeting_number_keeps_short_ordinal_candidate() -> None:
    uir = make_uir(
        [
            {
                "block_id": "opening",
                "type": "paragraph",
                "text": "2026年1月7日，县长主持召开县人民政府2026年第1次常务会议。",
            }
        ],
        metadata={"domain": "meeting_doc", "title": "2026年第1次常务会议"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_short_number", uir)
    number = next(item for item in candidates if item.source_name == "第1次")
    assert number.value_sample == "第1次"
    assert number.target_hints == ["meeting_number"]


def test_meeting_topic_preserves_learning_prefix() -> None:
    uir = make_uir(
        [
            {
                "block_id": "topic",
                "type": "paragraph",
                "text": "一、传达学习中央经济工作会议精神和中央农村工作会议精神",
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_topic_prefix", uir)
    topic = next(item for item in candidates if item.source_name == "传达学习")
    assert topic.target_hints == ["topics"]
    assert topic.source_blocks == ["topic"]


def test_meeting_department_attendees_stay_review_required() -> None:
    uir = make_uir(
        [
            {
                "block_id": "attendees",
                "type": "paragraph",
                "text": "会议强调，各乡镇、各部门单位要深入学习贯彻会议精神。",
            }
        ],
        metadata={"domain": "meeting_doc"},
    )

    candidates = CandidateService().extract_candidates("task_meeting_dept_attendees", uir)
    attendees = next(item for item in candidates if item.source_name == "各乡镇、各部门单位")
    assert attendees.target_hints == ["attendees"]
    assert "medium_risk_department_attendees" in attendees.quality_flags


def test_generic_labeled_meeting_date_keeps_existing_traceable_behavior() -> None:
    candidates = CandidateService().extract_candidates(
        "task_generic_meeting_date",
        make_uir(
            [
                {
                    "block_id": "date",
                    "type": "paragraph",
                    "text": "日期：2026-06-16 08:28",
                }
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    date = next(item for item in candidates if "meeting_date" in item.target_hints)
    assert date.value_sample == "2026-06-16"
    assert date.source_blocks == ["date"]
    assert date.evidence_type == "generic_labeled_meeting_date"


def test_meeting_source_line_can_support_organizer_review() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_source_organizer",
        make_uir(
            [
                {
                    "block_id": "source",
                    "type": "paragraph",
                    "text": "来源：汨罗市人民政府办公室",
                }
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    organizer = next(item for item in candidates if "organizer" in item.target_hints)
    assert organizer.source_name == "汨罗市人民政府办公室"
    assert organizer.value_sample == "汨罗市人民政府办公室"
    assert organizer.source_blocks == ["source"]
    assert "medium_risk_source_organizer" in organizer.quality_flags


def test_policy_semantic_candidates_preserve_issuer_and_publication_risk() -> None:
    uir = make_uir(
        [
            {
                "block_id": "publisher",
                "type": "paragraph",
                "text": "发布机构：市发展改革委",
            },
            {
                "block_id": "interpreter",
                "type": "paragraph",
                "text": "解读机构：市政策研究室",
            },
            {
                "block_id": "issue_date",
                "type": "paragraph",
                "text": "成文日期：2025年5月30日",
            },
        ],
        metadata={
            "domain": "policy_doc",
            "issuing_body": "市人民政府办公厅",
            "publication_date": "2025-06-01",
            "retrieved_at": "2025-06-02T10:00:00Z",
        },
    )

    candidates = CandidateService().extract_candidates("task_policy_semantics", uir)
    issuers = [item for item in candidates if "issuer" in item.target_hints]
    publish_dates = [item for item in candidates if "publish_date" in item.target_hints]

    assert any(
        item.value_sample == "市人民政府办公厅" and item.confidence_hint >= 0.82
        for item in issuers
    )
    assert any(
        item.value_sample == "市发展改革委"
        and item.confidence_hint <= 0.65
        and "medium_risk_issuer" in item.quality_flags
        and item.display_name == "发布机构"
        for item in issuers
    )
    assert not any(item.value_sample == "市政策研究室" for item in issuers)
    authoritative_dates = [
        item for item in publish_dates if not item.quality_flags
    ]
    issue_dates = [
        item for item in publish_dates if item.source_name == "成文日期"
    ]
    assert [item.value_sample for item in authoritative_dates] == ["2025-06-01"]
    assert issue_dates
    assert "medium_risk_issue_date_for_publish" in issue_dates[0].quality_flags
    assert issue_dates[0].source_blocks == ["issue_date"]
    assert publish_dates[0].evidence_type == "official_publication_metadata"


def test_general_conditions_and_service_object_emit_list_aware_hints() -> None:
    uir = make_uir(
        [
            {"block_id": "conditions", "type": "heading", "level": 2, "text": "申请条件"},
            {
                "block_id": "condition_list",
                "type": "list",
                "attributes": {"items": ["依法登记", "信用良好"]},
            },
            {
                "block_id": "object",
                "type": "paragraph",
                "text": "适用于本市科技型中小企业。",
            },
            {
                "block_id": "contact",
                "type": "paragraph",
                "text": "联系人：张三",
            },
        ],
        metadata={"domain": "general_doc"},
    )

    candidates = CandidateService().extract_candidates("task_general_semantics", uir)
    conditions = [
        item for item in candidates if "application_conditions" in item.target_hints
    ]
    service_objects = [
        item for item in candidates if "service_object" in item.target_hints
    ]

    assert conditions[0].value_sample == "依法登记\n信用良好"
    assert conditions[0].inferred_type == "list_like"
    assert conditions[0].source_blocks == ["conditions", "condition_list"]
    assert service_objects[0].value_sample == "本市科技型中小企业"
    assert service_objects[0].source_blocks == ["object"]
    assert not any(item.value_sample == "张三" for item in service_objects)


def test_general_application_guides_emit_labeled_role_and_process_hints() -> None:
    candidates = CandidateService().extract_candidates(
        "task_general_application_guide",
        make_uir(
            [
                {
                    "block_id": "role",
                    "type": "paragraph",
                    "text": "申报主体要求：本市企业，须与本市养老机构联合申报。",
                },
                {
                    "block_id": "leader",
                    "type": "paragraph",
                    "text": "项目负责人要求：申请者年龄应未满35周岁。",
                },
                {
                    "block_id": "online",
                    "type": "paragraph",
                    "text": "1.项目申报采用网上申报方式，无需送交纸质材料。",
                },
                {
                    "block_id": "overview",
                    "type": "paragraph",
                    "text": "拟申请进出口权的企业，需做好以下五步。具体办理流程如下。",
                },
                {
                    "block_id": "condition",
                    "type": "paragraph",
                    "text": "企业查看营业执照，经营范围中需含“货物进出口”等表述。",
                },
            ],
            metadata={"domain": "general_doc"},
        ),
    )

    service_objects = [
        item for item in candidates if "service_object" in item.target_hints
    ]
    process_steps = [item for item in candidates if "process_steps" in item.target_hints]
    conditions = [
        item for item in candidates if "application_conditions" in item.target_hints
    ]

    assert {item.source_name for item in service_objects} >= {
        "申报主体要求",
        "项目负责人要求",
        "拟申请企业",
    }
    assert {item.source_name for item in process_steps} >= {
        "申报方式",
        "五步走办理流程",
    }
    assert any(
        item.source_name == "经营范围中需含货物进出口" for item in conditions
    )


def test_meeting_topic_evidence_uses_stable_contextual_source_labels() -> None:
    candidates = CandidateService().extract_candidates(
        "task_topic_labels",
        make_uir(
            [
                {
                    "block_id": "opening",
                    "type": "paragraph",
                    "text": (
                        "2025年12月19日下午，区长主持召开常务会议，"
                        "审议《政府工作报告》等事项。"
                    ),
                },
                {
                    "block_id": "first_item",
                    "type": "paragraph",
                    "text": "会议听取区府办关于年度重点工作的汇报。",
                },
                {
                    "block_id": "numbered",
                    "type": "paragraph",
                    "text": "一、传达学习中央重要会议精神",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    topics = [item for item in candidates if "topics" in item.target_hints]
    assert {item.source_name for item in topics} >= {
        "reviewed matters",
        "first agenda item",
        "传达学习",
    }


def test_meeting_date_evidence_preserves_semantic_and_raw_labels() -> None:
    semantic = CandidateService().extract_candidates(
        "task_semantic_date",
        make_uir(
            [
                {"block_id": "title", "type": "heading", "text": "会议纪要"},
                {"block_id": "number", "type": "paragraph", "text": "第47次"},
                {
                    "block_id": "date",
                    "type": "paragraph",
                    "text": "2025年7月30日，市长主持召开市政府第47次常务会议。",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )
    semantic_date = next(
        item for item in semantic if "meeting_date" in item.target_hints
    )
    assert semantic_date.source_name == semantic_date.value_sample
    assert semantic_date.display_name == "meeting_date"
    assert semantic_date.value_sample == "2025年7月30日"

    standalone = CandidateService().extract_candidates(
        "task_standalone_date",
        make_uir(
            [
                {
                    "block_id": "date",
                    "type": "paragraph",
                    "text": "（二〇二五年十一月三日）",
                }
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )
    standalone_date = next(
        item for item in standalone if "meeting_date" in item.target_hints
    )
    assert standalone_date.source_name == "二〇二五年十一月三日"

    partial = CandidateService().extract_candidates(
        "task_partial_date",
        make_uir(
            [
                {
                    "block_id": "date",
                    "type": "paragraph",
                    "text": "5月20日，县长主持召开县政府常务会议。",
                }
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )
    partial_date = next(item for item in partial if "meeting_date" in item.target_hints)
    assert partial_date.source_name == "5月20日"
    assert "medium_risk_partial_date" in partial_date.quality_flags


def test_meeting_partial_date_from_source_url_stays_review_required() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_partial_year",
        make_uir(
            [
                {
                    "block_id": "opening",
                    "type": "paragraph",
                    "text": (
                        "5月20日，县委副书记、代县长李靖主持召开"
                        "县十六届政府第49次常务（扩大）会议。"
                    ),
                }
            ],
            metadata={
                "domain": "meeting_doc",
                "source_url": "https://www.zhenping.gov.cn/2026/06-15/1412478.html",
            },
        ),
    )

    meeting_date = next(item for item in candidates if item.display_name == "meeting_date")

    assert meeting_date.value_sample == "5月20日"
    assert meeting_date.evidence_type == "meeting_opening_date"
    assert "medium_risk_partial_date" in meeting_date.quality_flags
    assert "year_inferred_from_metadata" not in meeting_date.quality_flags


def test_meeting_standalone_full_date_beats_partial_opening_date() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_full_date",
        make_uir(
            [
                {"block_id": "date", "type": "paragraph", "text": "（二〇二五年十一月三日）"},
                {
                    "block_id": "opening",
                    "type": "paragraph",
                    "text": "11 月3 日，县委副书记、县长黄国杰主持召开十九届县政府第97次常务会议。",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    meeting_date = next(item for item in candidates if item.display_name == "meeting_date")

    assert meeting_date.value_sample == "二〇二五年十一月三日"
    assert meeting_date.source_blocks == ["date"]


def test_policy_signature_emits_source_backed_issuer_and_signed_date_labels() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_signature_labels",
        make_uir(
            [
                {
                    "block_id": "index",
                    "type": "table",
                    "attributes": {
                        "rows": [
                            {
                                "field": "信息索引",
                                "value": "生成日期：2025-03-18 | 发文机构：教育部",
                            }
                        ]
                    },
                },
                {"block_id": "issuer", "type": "paragraph", "text": "教 育 部"},
                {"block_id": "date", "type": "paragraph", "text": "2025年1月3日"},
            ],
            metadata={
                "domain": "policy_doc",
                "title": "教育部关于印发管理办法的通知",
                "source_url": (
                    "https://www.moe.gov.cn/srcsite/A29/202503/"
                    "t20250326_1184786.html"
                ),
            },
        ),
    )

    issuer = next(
        item
        for item in candidates
        if "issuer" in item.target_hints and item.source_blocks == ["issuer"]
    )
    signed_date = next(
        item for item in candidates if item.source_name == "signed date"
    )
    assert issuer.source_name == "发文机构"
    assert signed_date.target_hints == ["publish_date"]
    assert signed_date.source_blocks == ["date"]


def test_general_application_requirements_remain_reviewable() -> None:
    candidates = CandidateService().extract_candidates(
        "task_requirements_review",
        make_uir(
                [
                {"block_id": "heading", "type": "heading", "text": "二、申报要求"},
                {
                    "block_id": "body",
                    "type": "paragraph",
                    "text": "申请单位应依法登记并信用良好。",
                },
            ],
            metadata={"domain": "general_doc"},
        ),
    )

    requirements = next(
        item
        for item in candidates
        if item.source_name == "申报要求"
        and "application_conditions" in item.target_hints
    )
    assert "medium_risk_section_scope" in requirements.quality_flags


def test_source_site_and_deadline_candidates_have_safe_target_hints() -> None:
    candidates = CandidateService().extract_candidates(
        "task_source_deadline",
        make_uir(
            [
                {
                    "block_id": "deadline",
                    "type": "paragraph",
                    "text": "项目网上填报截止时间为2026年7月23日16:30。",
                }
            ],
            metadata={
                "domain": "general_doc",
                "source_site": "www.example.gov.cn",
            },
        ),
    )

    source = candidate_by_name(candidates, "source_site")
    deadline = next(item for item in candidates if "deadline" in item.target_hints)
    assert source.target_hints == ["source"]
    assert source.evidence_type == "official_source_metadata"
    assert deadline.source_name == "截止时间"
    assert deadline.source_blocks == ["deadline"]
    assert deadline.evidence_type == "explicit_deadline"


def test_policy_attachment_url_and_responsible_departments_are_risk_aware() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_attachment",
        make_uir(
            [
                {
                    "block_id": "responsible",
                    "type": "paragraph",
                    "text": (
                        "第三条 工业和信息化部负责制定管理政策，"
                        "国家发展改革委、生态环境部等部门按照职责分工负责监督管理。"
                    ),
                }
            ],
            metadata={
                "domain": "policy_doc",
                "source_url": (
                    "https://www.gov.cn/zhengce/zhengceku/202511/"
                    "P020251106333013261545.pdf"
                ),
            },
        ),
    )

    publish_date = next(
        item for item in candidates if "publish_date" in item.target_hints
    )
    issuer = next(
        item
        for item in candidates
        if item.source_name == "工业和信息化部等部门"
    )
    assert publish_date.value_sample == "2025-11-06"
    assert publish_date.evidence_type == "official_attachment_url"
    assert issuer.target_hints == ["issuer"]
    assert "medium_risk_responsible_departments" in issuer.quality_flags
    assert issuer.source_blocks == ["responsible"]


def test_policy_law_enacting_body_can_supply_required_issuer() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_law_issuer",
        make_uir(
            [
                {
                    "block_id": "history",
                    "type": "paragraph",
                    "text": (
                        "1995年10月30日第八届全国人民代表大会常务委员会"
                        "第十六次会议通过"
                    ),
                }
            ],
            metadata={
                "domain": "policy_doc",
                "title": "中华人民共和国民用航空法（2026年7月1日起施行）",
            },
        ),
    )

    issuer = next(
        item
        for item in candidates
        if item.evidence_type == "policy_law_enacting_body"
    )
    assert issuer.source_name == "全国人民代表大会常务委员会"
    assert issuer.target_hints == ["issuer"]
    assert issuer.source_blocks == ["history"]


def test_meeting_number_with_parenthetical_and_action_item_are_extracted() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_actions",
        make_uir(
            [
                {
                    "block_id": "opening",
                    "type": "paragraph",
                    "text": "县十六届政府第49次常务（扩大）会议纪要",
                },
                {
                    "block_id": "requirement",
                    "type": "paragraph",
                    "text": "会议要求，深入学习领会法典的核心要义。",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    meeting_number = next(
        item for item in candidates if item.display_name == "meeting_number"
    )
    action_item = next(
        item for item in candidates if item.display_name == "action_items"
    )
    assert meeting_number.source_name == "第49次"
    assert meeting_number.target_hints == ["meeting_number"]
    assert action_item.source_name == "会议要求"
    assert action_item.target_hints == ["action_items"]
    assert action_item.source_blocks == ["requirement"]


def test_meeting_opening_keeps_full_meeting_number_and_agenda_count_aliases() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_full_number",
        make_uir(
            [
                {
                    "block_id": "opening",
                    "type": "paragraph",
                    "text": (
                        "2026年2月11日，区委副书记、政府区长翟云驰主持召开"
                        "海勃湾区人民政府2026年第2次常务会议，研究审议9项议题。"
                        "现将会议议定事项纪要如下。"
                    ),
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    assert candidate_by_name(candidates, "2026年第2次常务会议").target_hints == [
        "meeting_number"
    ]
    topics = candidate_by_name(candidates, "研究审议9项议题")
    assert topics.target_hints == ["topics"]
    assert topics.source_blocks == ["opening"]


def test_meeting_numbered_agenda_headings_keep_specific_topic_source_names() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_topic_headings",
        make_uir(
            [
                {
                    "block_id": "ecology",
                    "type": "paragraph",
                    "text": "一、传达学习习近平总书记关于生态环境保护的重要讲话和重要指示批示精神",
                },
                {
                    "block_id": "safety",
                    "type": "paragraph",
                    "text": "二、听取安全生产工作情况汇报",
                },
                {
                    "block_id": "city",
                    "type": "paragraph",
                    "text": "三、传达市政府常务会议精神",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    ecology_topic = candidate_by_name(
        candidates, "传达学习习近平总书记关于生态环境保护"
    )
    safety_topic = candidate_by_name(candidates, "听取安全生产工作情况汇报")
    city_topic = candidate_by_name(candidates, "传达市政府常务会议精神")
    assert ecology_topic.target_hints == ["topics"]
    assert ecology_topic.source_blocks == ["ecology"]
    assert safety_topic.target_hints == ["topics"]
    assert safety_topic.source_blocks == ["safety"]
    assert city_topic.target_hints == ["topics"]
    assert city_topic.source_blocks == ["city"]


def test_meeting_decision_source_name_matches_principle_phrase() -> None:
    candidates = CandidateService().extract_candidates(
        "task_meeting_decisions",
        make_uir(
            [
                {
                    "block_id": "agree",
                    "type": "paragraph",
                    "text": "会议原则 同意《乌鲁木齐县生态环境保护工作情况报告》。",
                },
                {
                    "block_id": "pass",
                    "type": "paragraph",
                    "text": "原则通过《安全生产工作方案》。",
                },
                {
                    "block_id": "compound",
                    "type": "paragraph",
                    "text": "会议研究审议并原则同意《政府工作报告（送审稿）》。",
                },
                {
                    "block_id": "emphasis",
                    "type": "paragraph",
                    "text": "会议强调，各乡镇、各部门单位要深入学习贯彻会议精神。",
                },
            ],
            metadata={"domain": "meeting_doc"},
        ),
    )

    agree = candidate_by_name(candidates, "会议原则同意")
    passed = candidate_by_name(candidates, "原则通过")
    compound = candidate_by_name(candidates, "原则同意")
    action_item = candidate_by_name(candidates, "会议强调")
    assert agree.target_hints == ["decisions"]
    assert agree.source_blocks == ["agree"]
    assert passed.target_hints == ["decisions"]
    assert passed.source_blocks == ["pass"]
    assert compound.target_hints == ["decisions"]
    assert compound.source_blocks == ["compound"]
    assert action_item.target_hints == ["action_items"]
    assert action_item.source_blocks == ["emphasis"]


def test_meeting_mapping_prefers_specific_source_labels_over_generic_aliases() -> None:
    uir = make_uir(
        [
            {
                "block_id": "title",
                "type": "heading",
                "text": "市政府第62次常务会议纪要",
                "level": 1,
            },
            {
                "block_id": "opening",
                "type": "paragraph",
                "text": (
                    "2026年1月30日，张伟市长主持召开市政府第62次常务会议，"
                    "会议听取安全生产工作情况汇报。"
                ),
            },
            {
                "block_id": "decision",
                "type": "paragraph",
                "text": "（一）原则通过《安全生产工作方案》。",
            },
        ],
        metadata={
            "domain": "meeting_doc",
            "doc_type": "meeting_doc",
            "source_url": "https://example.gov.cn/meeting.html",
            "title": "市政府第62次常务会议纪要",
        },
    )

    report = mapping_report(uir, "meeting_doc", "meeting_doc_base_v1")
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["meeting_number"]["source_field"]["source_name"] == "第62次常务会议"
    assert mappings["topics"]["source_field"]["source_name"] == "听取安全生产工作情况汇报"
    assert mappings["decisions"]["source_field"]["source_name"] == "原则通过"


def test_policy_addressee_and_instruction_candidates_are_extracted() -> None:
    candidates = CandidateService().extract_candidates(
        "task_policy_addressee",
        make_uir(
            [
                {
                    "block_id": "audience",
                    "type": "paragraph",
                    "text": "各省、自治区、直辖市中小企业主管部门：",
                },
                {
                    "block_id": "measure",
                    "type": "paragraph",
                    "text": "现将办法印发给你们，请结合实际认真抓好落实。",
                },
            ],
            metadata={"domain": "policy_doc"},
        ),
    )

    audience = next(
        item
        for item in candidates
        if item.source_name == "各省中小企业主管部门"
    )
    measure = next(
        item for item in candidates if item.source_name == "结合实际抓好落实"
    )
    assert audience.target_hints == ["target_audience"]
    assert audience.source_blocks == ["audience"]
    assert measure.target_hints == ["policy_measures"]
    assert measure.source_blocks == ["measure"]


def test_policy_mapping_prefers_explicit_issuer_label_over_standalone_body() -> None:
    uir = make_uir(
        [
            {
                "block_id": "issuer_label",
                "type": "paragraph",
                "text": "发文机关：工业和信息化部",
            },
            {
                "block_id": "issuer_signature",
                "type": "paragraph",
                "text": "工业和信息化部",
            },
        ],
        metadata={
            "domain": "policy_doc",
            "doc_type": "policy_doc",
            "title": "工业和信息化部关于印发政策的通知",
            "source_url": "https://example.gov.cn/policy.html",
        },
    )

    report = mapping_report(uir, "policy_doc", "policy_doc_base_v1")
    mappings = {item["target_field_id"]: item for item in report.mappings}

    assert mappings["issuer"]["source_field"]["source_name"] == "发文机关"
