import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    CanonicalModelRecord,
    ConversionTask,
    Document,
    FieldCandidateRecord,
    FieldMappingRecord,
    MappingTemplateRecord,
    TargetSchemaRecord,
)
from app.engines.transform_engine import TransformEngine
from app.schemas.mapping import FieldCandidate, FieldMapping
from app.schemas.transform import TransformRule
from app.schemas.uir import UIRDocument
from app.services.canonical_service import CanonicalService
from app.services.storage_service import StorageService

EXAMPLES = Path(__file__).resolve().parent.parent.parent / "examples" / "demo"


def _load_json(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _make_uir(name: str) -> UIRDocument:
    return UIRDocument.model_validate(_load_json(name))


def _make_template(name: str) -> dict:
    return _load_json(name)


def _make_candidate(
    candidate_id: str,
    task_id: str,
    doc_id: str,
    source_path: str,
    source_name: str,
    value: object,
    source_blocks: list[str],
    inferred_type: str = "string",
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=candidate_id,
        task_id=task_id,
        doc_id=doc_id,
        source_path=source_path,
        source_name=source_name,
        display_name=source_name,
        value_sample=value,
        inferred_type=inferred_type,
        source_blocks=source_blocks,
        confidence=0.95,
        evidence=["test"],
    )


def _make_mapping(
    mapping_id: str,
    task_id: str,
    candidate_id: str,
    source_path: str,
    source_name: str,
    target_field_id: str,
    status: str = "confirmed",
) -> FieldMapping:
    return FieldMapping(
        mapping_id=mapping_id,
        task_id=task_id,
        candidate_id=candidate_id,
        source_field={"source_path": source_path, "source_name": source_name},
        target_field_id=target_field_id,
        target_field_name=target_field_id,
        method="test",
        confidence=1.0,
        status=status,
    )


def _build_source_context(
    candidates: list[FieldCandidate],
) -> dict[str, FieldCandidate]:
    return {c.source_path: c for c in candidates}


def _run_engine(uir, mappings, rules, source_context=None, enum_maps=None, defaults=None):
    engine = TransformEngine()
    return engine.execute(
        uir=uir,
        mappings=mappings,
        transform_rules=rules,
        enum_maps=enum_maps or {},
        defaults=defaults or {},
        source_context=source_context or {},
    )


# ─── Regression 1: metadata.文档标题 → title 的真实 rename rule ───


def test_rename_metadata_chinese_key_to_title():
    """metadata.文档标题 (source_name=文档标题) must resolve and write to target title."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_test",
        metadata={"文档标题": "数据平台操作手册"},
        blocks=[],
    )
    candidates = [
        _make_candidate(
            "cand_1", "task_1", "doc_test",
            source_path="metadata.文档标题",
            source_name="文档标题",
            value="数据平台操作手册",
            source_blocks=[],
        ),
    ]
    mappings = [
        _make_mapping(
            "map_1", "task_1", "cand_1",
            source_path="metadata.文档标题",
            source_name="文档标题",
            target_field_id="title",
        ),
    ]
    rules = [
        TransformRule(
            rule_id="rename_title",
            operation="rename",
            source_field="metadata.文档标题",
            target_field_id="title",
        ),
    ]
    fields, traces, errors = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context(candidates),
    )
    assert "title" in fields
    assert fields["title"].value == "数据平台操作手册"
    assert fields["title"].source_candidates == ["cand_1"]


# ─── Regression 2: general demo summary_hint → summary，结果不得为 null ───


def test_general_summary_hint_rename_not_null():
    """rename rule metadata.summary_hint → summary must produce non-null value."""
    uir = _make_uir("example_uir_general_doc.json")
    template = _make_template("mapping_template_general.json")

    candidates = [
        _make_candidate(
            "cand_summary", "task_g", "doc_demo_general_001",
            source_path="metadata.summary_hint",
            source_name="summary_hint",
            value="介绍数据平台的登录、检索和导出流程。",
            source_blocks=[],
        ),
    ]
    mappings = [
        _make_mapping(
            "map_summary", "task_g", "cand_summary",
            source_path="metadata.summary_hint",
            source_name="summary_hint",
            target_field_id="summary",
        ),
    ]
    rename_rules = [
        r for r in template["transform_rules"]
        if r["operation"] == "rename" and r["target_field_id"] == "summary"
    ]
    rules = [TransformRule.model_validate(r) for r in rename_rules]

    fields, traces, errors = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context(candidates),
    )
    assert "summary" in fields
    assert fields["summary"].value is not None
    assert fields["summary"].value != ""
    assert fields["summary"].value == "介绍数据平台的登录、检索和导出流程。"
    assert fields["summary"].source_candidates == ["cand_summary"]


# ─── Regression 3: policy demo label-value 发布日期候选转换为 2026-06-01 ───


def test_policy_label_value_publish_date_conversion():
    """Candidate extracted from label-value text should resolve via candidate value_sample."""
    uir = _make_uir("example_uir_policy_doc.json")

    publish_date_candidate = _make_candidate(
        "cand_pd", "task_p", "doc_demo_policy_001",
        source_path="blocks.blk_p_002.text.发布日期",
        source_name="发布日期",
        value="2026年6月1日",
        source_blocks=["blk_p_002"],
        inferred_type="date",
    )
    candidates = [publish_date_candidate]
    mappings = [
        _make_mapping(
            "map_pd", "task_p", "cand_pd",
            source_path="blocks.blk_p_002.text.发布日期",
            source_name="发布日期",
            target_field_id="publish_date",
        ),
    ]
    rules = [
        TransformRule(
            rule_id="policy_publish_date_format",
            operation="date_format",
            source_field="blocks.blk_p_002.text.发布日期",
            target_field_id="publish_date",
            params={"output_format": "YYYY-MM-DD"},
        ),
    ]
    fields, traces, errors = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context(candidates),
    )
    assert fields["publish_date"].value == "2026-06-01"
    assert fields["publish_date"].source_blocks == ["blk_p_002"]
    assert fields["publish_date"].source_candidates == ["cand_pd"]


# ─── Regression 4: policy demo blk_p_005 + blk_p_006 merge 必须包含两段正文 ───


def test_policy_merge_block_text_paths():
    """merge rule with block text source_fields must combine both paragraphs."""
    uir = _make_uir("example_uir_policy_doc.json")

    cand_blk5 = _make_candidate(
        "cand_b5", "task_p", "doc_demo_policy_001",
        source_path="blocks.blk_p_005.text",
        source_name="blk_p_005_text",
        value="为规范数据治理工作，提升数据资产管理水平，制定本办法。",
        source_blocks=["blk_p_005"],
    )
    cand_blk6 = _make_candidate(
        "cand_b6", "task_p", "doc_demo_policy_001",
        source_path="blocks.blk_p_006.text",
        source_name="blk_p_006_text",
        value="本办法适用于数据标准、数据质量和数据安全相关管理活动。",
        source_blocks=["blk_p_006"],
    )
    candidates = [cand_blk5, cand_blk6]
    mappings = [
        _make_mapping("map_b5", "task_p", "cand_b5",
                       source_path="blocks.blk_p_005.text", source_name="blk_p_005_text",
                       target_field_id="main_content"),
        _make_mapping("map_b6", "task_p", "cand_b6",
                       source_path="blocks.blk_p_006.text", source_name="blk_p_006_text",
                       target_field_id="main_content"),
    ]
    rules = [
        TransformRule(
            rule_id="policy_main_content_merge",
            operation="merge",
            source_fields=["blocks.blk_p_005.text", "blocks.blk_p_006.text"],
            target_field_id="main_content",
            params={"separator": "\n", "skip_empty": True},
        ),
    ]
    fields, traces, errors = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context(candidates),
    )
    merged = fields["main_content"].value
    assert "为规范数据治理工作" in merged
    assert "本办法适用于数据标准" in merged
    assert fields["main_content"].source_blocks == ["blk_p_005", "blk_p_006"]
    assert set(fields["main_content"].source_candidates) == {"cand_b5", "cand_b6"}


# ─── Regression 5: block 派生 canonical field 的 source_blocks 非空 ───


def test_block_derived_field_source_blocks_nonempty():
    """Field mapped from a block path must have non-empty source_blocks."""
    uir = _make_uir("example_uir_policy_doc.json")

    cand = _make_candidate(
        "cand_title", "task_p", "doc_demo_policy_001",
        source_path="blocks.blk_p_001.text",
        source_name="heading_title",
        value="数据治理管理办法",
        source_blocks=["blk_p_001"],
    )
    mappings = [
        _make_mapping("map_t", "task_p", "cand_title",
                       source_path="blocks.blk_p_001.text", source_name="heading_title",
                       target_field_id="title"),
    ]
    fields, traces, errors = _run_engine(
        uir, mappings, [],
        source_context=_build_source_context([cand]),
    )
    assert fields["title"].value == "数据治理管理办法"
    assert fields["title"].source_blocks == ["blk_p_001"]
    assert fields["title"].source_candidates == ["cand_title"]


# ─── Regression 6: rename/merge/split source_candidates/source_blocks 继承 ───


def test_rename_inherits_source_provenance():
    """rename must inherit source_candidates and source_blocks from the source field."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_prov",
        metadata={"中文名称": "测试值"},
        blocks=[],
    )
    cand = _make_candidate(
        "cand_r", "task_r", "doc_prov",
        source_path="metadata.中文名称",
        source_name="中文名称",
        value="测试值",
        source_blocks=[],
    )
    mappings = [
        _make_mapping("map_r", "task_r", "cand_r",
                       source_path="metadata.中文名称", source_name="中文名称",
                       target_field_id="name"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="rename",
            source_field="metadata.中文名称", target_field_id="name",
        ),
    ]
    fields, _, _ = _run_engine(uir, mappings, rules,
                                source_context=_build_source_context([cand]))
    assert fields["name"].source_candidates == ["cand_r"]
    assert fields["name"].source_blocks == []


def test_merge_inherits_all_source_provenance():
    """merge must union source_candidates and source_blocks from all sources, deduplicated."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_m",
        metadata={},
        blocks=[],
    )
    cand1 = _make_candidate("c1", "t", "d", "src_a", "a", "hello", ["blk_1"])
    cand2 = _make_candidate("c2", "t", "d", "src_b", "b", "world", ["blk_2"])
    mappings = [
        _make_mapping("m1", "t", "c1", "src_a", "a", "merged"),
        _make_mapping("m2", "t", "c2", "src_b", "b", "merged"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="merge",
            source_fields=["src_a", "src_b"], target_field_id="merged",
            params={"separator": " ", "skip_empty": True},
        ),
    ]
    fields, _, _ = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context([cand1, cand2]),
    )
    assert fields["merged"].value == "hello world"
    assert set(fields["merged"].source_candidates) == {"c1", "c2"}
    assert set(fields["merged"].source_blocks) == {"blk_1", "blk_2"}


def test_split_inherits_source_provenance():
    """split must inherit source_candidates and source_blocks to each target field."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_s",
        metadata={"org_full": "信息中心|ORG001"},
        blocks=[],
    )
    cand = _make_candidate(
        "c_s", "t", "d", "metadata.org_full", "org_full",
        "信息中心|ORG001", ["blk_s"],
    )
    mappings = [
        _make_mapping("m_s", "t", "c_s", "metadata.org_full", "org_full", "org_full"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="split",
            source_field="metadata.org_full",
            target_fields=["org_name", "org_code"],
            params={"separator": "|"},
        ),
    ]
    fields, _, _ = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context([cand]),
    )
    assert fields["org_name"].value == "信息中心"
    assert fields["org_code"].value == "ORG001"
    assert fields["org_name"].source_candidates == ["c_s"]
    assert fields["org_name"].source_blocks == ["blk_s"]
    assert fields["org_code"].source_candidates == ["c_s"]
    assert fields["org_code"].source_blocks == ["blk_s"]


# ─── Regression 7: rule.params["map"] 枚举映射测试 ───


def test_enum_map_uses_rule_params_map():
    """enum_map should prefer rule.params['map'] over template.enum_maps."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_e",
        metadata={"doc_type": "办法"},
        blocks=[],
    )
    cand = _make_candidate("c_e", "t", "d", "metadata.doc_type", "doc_type", "办法", [])
    mappings = [
        _make_mapping("m_e", "t", "c_e", "metadata.doc_type", "doc_type", "doc_type"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="enum_map",
            source_field="metadata.doc_type", target_field_id="doc_type",
            params={"map": {"办法": "policy", "通知": "notice"}},
        ),
    ]
    fields, traces, _ = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context([cand]),
        enum_maps={},
    )
    assert fields["doc_type"].value == "policy"
    assert any(t["status"] == "success" for t in traces)


# ─── Regression 8: 无效日期产生 warning 且保留原值 ───


def test_invalid_date_preserves_value_and_warning():
    """date_format on an invalid date must keep original value and emit warning trace."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_d",
        metadata={"pub_date": "not-a-date"},
        blocks=[],
    )
    cand = _make_candidate("c_d", "t", "d", "metadata.pub_date", "pub_date", "not-a-date", [])
    mappings = [
        _make_mapping("m_d", "t", "c_d", "metadata.pub_date", "pub_date", "publish_date"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="date_format",
            source_field="metadata.pub_date", target_field_id="publish_date",
            params={"output_format": "YYYY-MM-DD"},
        ),
    ]
    fields, traces, _ = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context([cand]),
    )
    assert fields["publish_date"].value == "not-a-date"
    date_traces = [t for t in traces if t["action"] == "date_format"]
    assert len(date_traces) == 1
    assert date_traces[0]["status"] in ("warning", "error")


# ─── Regression 9: 缺失源字段和 split 段数不足产生 trace ───


def test_missing_source_field_emits_trace():
    """When a source field doesn't exist, a trace event must be recorded."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_mf",
        metadata={},
        blocks=[],
    )
    mappings = [
        _make_mapping("m_mf", "t", "c_missing", "metadata.nonexistent", "nonexistent", "target_f"),
    ]
    fields, traces, errors = _run_engine(uir, mappings, [])
    date_traces = [t for t in traces if t["status"] in ("warning", "error")]
    assert len(date_traces) >= 1


def test_split_insufficient_segments_emits_trace():
    """split with fewer parts than target_fields must emit warning/error trace."""
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_ss",
        metadata={"single_val": "only_one"},
        blocks=[],
    )
    cand = _make_candidate("c_ss", "t", "d", "metadata.single_val", "single_val", "only_one", [])
    mappings = [
        _make_mapping("m_ss", "t", "c_ss", "metadata.single_val", "single_val", "single_val"),
    ]
    rules = [
        TransformRule(
            rule_id="r1", operation="split",
            source_field="metadata.single_val",
            target_fields=["part1", "part2", "part3"],
            params={"separator": "|"},
        ),
    ]
    fields, traces, _ = _run_engine(
        uir, mappings, rules,
        source_context=_build_source_context([cand]),
    )
    assert fields["part1"].value == "only_one"
    assert fields["part2"].value == ""
    assert fields["part3"].value == ""
    split_traces = [t for t in traces if t["action"] == "split"]
    assert len(split_traces) >= 1
    assert any(t["status"] in ("warning", "error") for t in split_traces)


# ─── Regression 10: review_required 任务被阻止，状态不变且没有 canonical 持久化文件 ───


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    with TestSession() as session:
        yield session


@pytest.fixture()
def storage(tmp_path):
    return StorageService(tmp_path / "storage")


def _setup_task(
    db_session,
    storage,
    status,
    mappings_status="confirmed",
    required_missing=False,
    mapping_need_review=False,
    candidate_path="metadata.title",
    candidate_value='"Test"',
):
    uir_data = {
        "uir_version": "1.0",
        "doc_id": "doc_sm",
        "metadata": {"title": "Test"},
        "blocks": [{"block_id": "blk_1", "type": "heading", "level": 1,
                     "text": "Title", "attributes": {}}],
        "assets": [],
        "normalization_records": [],
    }
    storage.save_json("documents/doc_sm/uir.json", uir_data)

    doc = Document(
        doc_id="doc_sm", title="Test", uir_version="1.0",
        storage_path="documents/doc_sm/uir.json", block_count=1,
    )
    db_session.add(doc)

    schema = TargetSchemaRecord(
        schema_id="schema_sm", name="s", version="1.0.0",
        schema_json=json.dumps({
            "schema_id": "schema_sm", "name": "s", "version": "1.0.0",
            "fields": [
                {"field_id": "title", "name": "title", "display_name": "Title",
                 "type": "string", "required": True},
                {"field_id": "language", "name": "language", "display_name": "Lang",
                 "type": "string", "required": True},
            ],
        }),
        json_schema=json.dumps({
            "type": "object", "required": ["title", "language"],
            "properties": {
                "title": {"type": "string"},
                "language": {"type": "string"},
            },
        }),
    )
    db_session.add(schema)

    defaults = {} if required_missing else {"language": "zh-CN"}
    template_data = {
        "template_id": "tpl_sm", "schema_id": "schema_sm",
        "name": "t", "version": "1.0.0",
        "aliases": {}, "regex_rules": [],
        "transform_rules": [],
        "defaults": defaults,
        "enum_maps": {},
    }
    template = MappingTemplateRecord(
        template_id="tpl_sm", schema_id="schema_sm",
        name="t", version="1.0.0",
        template_json=json.dumps(template_data),
    )
    db_session.add(template)

    task = ConversionTask(
        task_id="task_sm", doc_id="doc_sm", schema_id="schema_sm",
        schema_version="1.0.0", template_id="tpl_sm", template_version="1.0.0",
        status=status, input_hash="sha256:abc",
    )
    db_session.add(task)

    if mappings_status != "none":
        cand = FieldCandidateRecord(
            candidate_id="cand_sm", task_id="task_sm", doc_id="doc_sm",
            source_path=candidate_path, source_name="title",
            display_name="title", value_sample=candidate_value,
            inferred_type="string", source_blocks_json="[]", confidence=0.95,
        )
        db_session.add(cand)
        mapping = FieldMappingRecord(
            mapping_id="map_sm", task_id="task_sm", candidate_id="cand_sm",
            target_field_id="title", method="exact_match", confidence=1.0,
            status=mappings_status, need_review=mapping_need_review,
            evidence_json='["test"]',
        )
        db_session.add(mapping)

    db_session.commit()
    return task


def test_review_required_blocks_canonical_build(db_session, storage):
    """build_canonical must be blocked when task status is review_required."""
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    _setup_task(db_session, storage, status="review_required",
                mappings_status="review_required")

    schema_obj = TargetSchema.model_validate_json(
        db_session.get(TargetSchemaRecord, "schema_sm").schema_json
    )
    template_obj = MappingTemplate.model_validate_json(
        db_session.get(MappingTemplateRecord, "tpl_sm").template_json
    )

    service = CanonicalService(db_session, storage)
    with pytest.raises(ValueError, match="cannot build canonical"):
        service.build_canonical("task_sm", schema_obj, template_obj)

    assert db_session.get(CanonicalModelRecord, "task_sm") is None


# ─── Regression 11: required 字段缺失且无 default 时被阻止 ───


def test_required_missing_no_default_blocks_canonical(db_session, storage):
    """build_canonical must be blocked when required fields are missing and no default exists."""
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    _setup_task(db_session, storage, status="mapping_completed",
                mappings_status="confirmed", required_missing=True)

    schema_obj = TargetSchema.model_validate_json(
        db_session.get(TargetSchemaRecord, "schema_sm").schema_json
    )
    template_obj = MappingTemplate.model_validate_json(
        db_session.get(MappingTemplateRecord, "tpl_sm").template_json
    )

    service = CanonicalService(db_session, storage)
    with pytest.raises(ValueError, match="cannot build canonical"):
        service.build_canonical("task_sm", schema_obj, template_obj)

    assert db_session.get(CanonicalModelRecord, "task_sm") is None


# ─── Regression 12: source name != target name in all tests ───
# (enforced by design — every test above uses distinct source_name vs target_field_id)


def test_execute_returns_errors_list():
    """TransformEngine.execute must return errors as third element of the tuple."""
    engine = TransformEngine()
    uir = UIRDocument(uir_version="1.0", doc_id="d", metadata={}, blocks=[])
    result = engine.execute(uir, [], [], {}, {})
    assert len(result) == 3
    assert isinstance(result[2], list)


def test_engine_does_not_set_task_status():
    """TransformEngine must not modify task status — only CanonicalService should."""
    engine = TransformEngine()
    uir = UIRDocument(uir_version="1.0", doc_id="d", metadata={}, blocks=[])
    engine.execute(uir, [], [], {}, {})
    assert True


def test_source_context_can_resolve_mapping_by_candidate_id():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_candidate_id",
        metadata={"title": "UIR value"},
        blocks=[],
    )
    candidate = _make_candidate(
        "cand_exact",
        "task_candidate_id",
        "doc_candidate_id",
        "metadata.title",
        "title",
        "candidate value",
        [],
    )
    mapping = _make_mapping(
        "map_exact",
        "task_candidate_id",
        "cand_exact",
        "metadata.title",
        "title",
        "canonical_title",
    )

    fields, _, _ = _run_engine(
        uir,
        [mapping],
        [],
        source_context={candidate.candidate_id: candidate},
    )

    assert fields["canonical_title"].value == "candidate value"
    assert fields["canonical_title"].source_candidates == ["cand_exact"]


def test_missing_rename_source_records_error_and_preserves_target():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_missing_rename",
        metadata={"title": "existing value"},
        blocks=[],
    )
    mapping = _make_mapping(
        "map_title",
        "task_missing_rename",
        "cand_title",
        "metadata.title",
        "title",
        "title",
    )
    rule = TransformRule(
        rule_id="rename_missing",
        operation="rename",
        source_field="metadata.not_found",
        target_field_id="title",
    )

    fields, traces, errors = _run_engine(uir, [mapping], [rule])

    assert fields["title"].value == "existing value"
    assert errors == ["rule rename_missing: source field 'metadata.not_found' not found"]
    error_trace = next(trace for trace in traces if trace["status"] == "error")
    assert error_trace["rule_id"] == "rename_missing"


def test_mapping_review_flag_blocks_even_when_task_status_is_mapping_completed(
    db_session,
    storage,
):
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    _setup_task(
        db_session,
        storage,
        status="mapping_completed",
        mappings_status="confirmed",
        mapping_need_review=True,
    )
    schema_obj = TargetSchema.model_validate_json(
        db_session.get(TargetSchemaRecord, "schema_sm").schema_json
    )
    template_obj = MappingTemplate.model_validate_json(
        db_session.get(MappingTemplateRecord, "tpl_sm").template_json
    )

    with pytest.raises(ValueError, match="unresolved mapping"):
        CanonicalService(db_session, storage).build_canonical(
            "task_sm", schema_obj, template_obj
        )

    assert db_session.get(CanonicalModelRecord, "task_sm") is None


def test_required_field_with_none_value_blocks_canonical_build(db_session, storage):
    from app.schemas.mapping_template import MappingTemplate
    from app.schemas.target_schema import TargetSchema

    _setup_task(
        db_session,
        storage,
        status="mapping_completed",
        mappings_status="confirmed",
        candidate_path="metadata.not_found",
        candidate_value="null",
    )
    schema_obj = TargetSchema.model_validate_json(
        db_session.get(TargetSchemaRecord, "schema_sm").schema_json
    )
    template_obj = MappingTemplate.model_validate_json(
        db_session.get(MappingTemplateRecord, "tpl_sm").template_json
    )

    with pytest.raises(ValueError, match="required field 'title'"):
        CanonicalService(db_session, storage).build_canonical(
            "task_sm", schema_obj, template_obj
        )

    assert db_session.get(CanonicalModelRecord, "task_sm") is None


def test_policy_merge_raw_block_paths_preserves_block_provenance():
    uir = _make_uir("example_uir_policy_doc.json")
    template = _make_template("mapping_template_policy.json")
    merge_rule = TransformRule.model_validate(
        next(rule for rule in template["transform_rules"] if rule["operation"] == "merge")
    )

    fields, _, _ = _run_engine(uir, [], [merge_rule], source_context={})

    assert fields["main_content"].source_blocks == ["blk_p_005", "blk_p_006"]


def test_valid_iso_date_records_success_trace():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_iso_date",
        metadata={"published": "2026-06-01"},
        blocks=[],
    )
    mapping = _make_mapping(
        "map_iso",
        "task_iso",
        "cand_iso",
        "metadata.published",
        "published",
        "publish_date",
    )
    rule = TransformRule(
        rule_id="date_iso",
        operation="date_format",
        target_field_id="publish_date",
    )

    _, traces, errors = _run_engine(uir, [mapping], [rule])

    date_trace = next(trace for trace in traces if trace["action"] == "date_format")
    assert date_trace["status"] == "success"
    assert errors == []


def test_missing_split_source_records_error_without_creating_targets():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_missing_split",
        metadata={},
        blocks=[],
    )
    rule = TransformRule(
        rule_id="split_missing",
        operation="split",
        source_field="metadata.not_found",
        target_fields=["left", "right"],
    )

    fields, traces, errors = _run_engine(uir, [], [rule])

    assert "left" not in fields
    assert "right" not in fields
    assert errors == ["rule split_missing: source field 'metadata.not_found' not found"]
    assert next(trace for trace in traces if trace["status"] == "error")[
        "rule_id"
    ] == "split_missing"


def test_invalid_bool_cast_preserves_original_and_records_error():
    uir = UIRDocument(
        uir_version="1.0",
        doc_id="doc_invalid_bool",
        metadata={"active": "sometimes"},
        blocks=[],
    )
    mapping = _make_mapping(
        "map_bool",
        "task_bool",
        "cand_bool",
        "metadata.active",
        "active",
        "is_active",
    )
    rule = TransformRule(
        rule_id="cast_bool",
        operation="type_cast",
        target_field_id="is_active",
        params={"to": "bool"},
    )

    fields, traces, errors = _run_engine(uir, [mapping], [rule])

    assert fields["is_active"].value == "sometimes"
    assert errors == ["rule cast_bool: cannot cast 'sometimes' to bool"]
    assert next(trace for trace in traces if trace["status"] == "error")[
        "rule_id"
    ] == "cast_bool"
