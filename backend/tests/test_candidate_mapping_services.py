import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"
UIR_DIR = PRODUCTION_LIKE_DIR / "uir"


def load_uir(name: str):
    from app.schemas.uir import UIRDocument

    return UIRDocument.model_validate(json.loads((UIR_DIR / name).read_text(encoding="utf-8")))


def load_schema(schema_id: str):
    from app.services.schema_service import SchemaService

    return SchemaService(SCHEMAS_DIR).load_schema(schema_id)


def load_template(template_id: str):
    from app.services.template_service import TemplateService

    return TemplateService(TEMPLATES_DIR).load_template(template_id)


def test_candidate_service_extracts_metadata_table_and_block_candidates():
    from app.services.candidate_service import CandidateService

    uir = load_uir("policy/policy_002_alias_variants.json")
    candidates = CandidateService().extract_candidates("task_policy_002", uir)

    metadata_title = next(
        candidate
        for candidate in candidates
        if candidate.source_name == "通知名称" and candidate.source_path == "$.metadata.通知名称"
    )
    table_title = next(
        candidate
        for candidate in candidates
        if candidate.source_name == "通知名称"
        and candidate.source_path == "$.blocks.pol002_b002.rows.0"
    )
    body = next(candidate for candidate in candidates if candidate.source_name == "正文")

    assert metadata_title.inferred_type == "string"
    assert table_title.source_blocks == ["pol002_b002"]
    assert body.source_path == "$.blocks.pol002_b003.text"
    assert body.source_blocks == ["pol002_b003"]
    assert all(candidate.source_name != "domain" for candidate in candidates)


def test_candidate_service_handles_missing_metadata_and_empty_blocks():
    from app.schemas.uir import UIRDocument
    from app.services.candidate_service import CandidateService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc_empty",
            "metadata": {},
            "blocks": [],
            "assets": [],
            "normalization_records": [],
        }
    )

    assert CandidateService().extract_candidates("task_empty", uir) == []


def test_mapping_service_maps_exact_and_alias_methods():
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = load_uir("policy/policy_001_standard.json")
    schema = load_schema("policy_doc")
    template = load_template("policy_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_policy_001", uir)

    report = MappingService().map_fields(
        task_id="task_policy_001",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    by_target = {mapping["target_field_id"]: mapping for mapping in report.mappings}
    assert by_target["title"]["method"] == "alias"
    assert by_target["content"]["method"] == "exact"
    assert by_target["doc_type"]["method"] == "alias"
    assert report.summary["strategy_counts"]["alias"] >= 3
    assert report.summary["total_candidates"] == len(candidates)


def test_mapping_service_maps_regex_method_from_block_text():
    from app.schemas.uir import UIRDocument
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_regex",
            "metadata": {
                "标题": "正则摘要测试",
                "发文机关": "测试机关",
                "发布日期": "2024-01-01",
                "content": "正文内容",
            },
            "blocks": [
                {
                    "block_id": "blk_regex",
                    "type": "paragraph",
                    "text": "摘要：用于验证 regex strategy",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )
    schema = load_schema("policy_doc")
    template = load_template("policy_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_regex", uir)

    report = MappingService().map_fields(
        task_id="task_regex",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    by_target = {mapping["target_field_id"]: mapping for mapping in report.mappings}
    assert by_target["summary"]["method"] == "regex"
    assert by_target["summary"]["source_blocks"] == ["blk_regex"]
    assert report.summary["strategy_counts"]["regex"] == 1


def test_mapping_service_maps_type_method_for_text_content():
    from app.schemas.uir import UIRDocument
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "policy_type",
            "metadata": {
                "标题": "类型映射测试",
                "发文机关": "测试机关",
                "发布日期": "2024-01-01",
            },
            "blocks": [
                {
                    "block_id": "blk_content",
                    "type": "paragraph",
                    "text": "这是一段未使用标准字段名标注的正文。",
                    "attributes": {"field_name": "正文段落"},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )
    schema = load_schema("policy_doc")
    template = load_template("policy_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_type", uir)

    report = MappingService().map_fields(
        task_id="task_type",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    by_target = {mapping["target_field_id"]: mapping for mapping in report.mappings}
    assert by_target["content"]["method"] == "type"
    assert report.summary["strategy_counts"]["type"] == 1


def test_mapping_service_marks_fuzzy_low_confidence_as_review_required():
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = load_uir("policy/policy_002_alias_variants.json")
    schema = load_schema("policy_doc")
    template = load_template("policy_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_policy_002", uir)

    report = MappingService().map_fields(
        task_id="task_policy_002",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    review_pairs = {
        (item["source_field"]["source_name"], item["target_field_id"])
        for item in report.review_required_items
    }
    assert ("通知名称", "title") in review_pairs
    assert ("制定主体", "issuer") in review_pairs
    assert ("成文日期", "publish_date") in review_pairs
    assert report.summary["strategy_counts"]["fuzzy"] >= 3


def test_mapping_service_records_unmapped_required_fields():
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = load_uir("meeting/meeting_003_missing_required.json")
    schema = load_schema("meeting_doc")
    template = load_template("meeting_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_meeting_003", uir)

    report = MappingService().map_fields(
        task_id="task_meeting_003",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    assert any(item["target_field_id"] == "meeting_date" for item in report.unmapped)
    assert report.summary["unmapped_required_fields"] >= 1


def test_mapping_service_does_not_high_confidence_accept_badcase_source():
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService

    uir = load_uir("policy/policy_004_low_confidence.json")
    schema = load_schema("policy_doc")
    template = load_template("policy_doc_base_v1")
    candidates = CandidateService().extract_candidates("task_policy_004", uir)

    report = MappingService().map_fields(
        task_id="task_policy_004",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )

    high_confidence_badcase = [
        mapping
        for mapping in report.mappings
        if mapping["source_field"]["source_name"] == "责任主体"
        and mapping["target_field_id"] == "issuer"
        and mapping["confidence"] >= 0.9
    ]
    assert high_confidence_badcase == []
    assert any(
        item["source_field"]["source_name"] == "责任主体"
        for item in report.review_required_items
    )


def test_mapping_service_llm_fallback_stub_stays_review_required():
    from app.config import Settings
    from app.schemas.mapping import FieldCandidate
    from app.services.llm_fallback_service import LLMFallbackService
    from app.services.mapping_service import MappingService

    schema = load_schema("general_doc")
    template = load_template("general_doc_base_v1")
    uir = load_uir("general/general_001_standard.json")
    candidates = [
        FieldCandidate(
            candidate_id="cand_unknown",
            task_id="task_llm",
            doc_id=uir.doc_id,
            source_path="$.metadata.神秘字段",
            source_name="神秘字段",
            value_sample="需要人工判断",
            inferred_type="string",
            confidence=0.5,
            evidence=["test candidate"],
        )
    ]

    llm_service = LLMFallbackService(
        Settings(llm_fallback_enabled=True, llm_mode="mock", _env_file=None)
    )
    report = MappingService(llm_fallback_service=llm_service).map_fields(
        task_id="task_llm",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={"enable_llm_fallback": True},
    )

    assert report.summary["strategy_counts"]["llm_fallback"] >= 1
    assert all(item["need_review"] for item in report.review_required_items)
    assert any(
        "prompt_hash=" in evidence
        for item in report.review_required_items
        for evidence in item["evidence"]
    )


def test_llm_fallback_is_disabled_by_default_even_when_option_requested():
    from app.schemas.mapping import FieldCandidate
    from app.services.mapping_service import MappingService

    schema = load_schema("general_doc")
    template = load_template("general_doc_base_v1")
    uir = load_uir("general/general_001_standard.json")
    candidates = [
        FieldCandidate(
            candidate_id="cand_unknown",
            task_id="task_llm_disabled",
            doc_id=uir.doc_id,
            source_path="$.metadata.unknown_source",
            source_name="unknown_source",
            value_sample="needs review",
            inferred_type="string",
            confidence=0.5,
            evidence=["test candidate"],
        )
    ]

    report = MappingService().map_fields(
        task_id="task_llm_disabled",
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
        options={"enable_llm_fallback": True},
    )

    assert report.summary["strategy_counts"]["llm_fallback"] == 0


def test_llm_fallback_service_filters_badcase_suggestions():
    from app.schemas.mapping import FieldCandidate
    from app.schemas.target_schema import TargetField
    from app.services.llm_fallback_service import LLMFallbackService

    candidate = FieldCandidate(
        candidate_id="cand_responsibility",
        task_id="task_llm_badcase",
        doc_id="doc_badcase",
        source_path="$.metadata.责任主体",
        source_name="责任主体",
        value_sample="某责任单位",
        inferred_type="string",
        confidence=0.5,
    )
    field = TargetField(
        field_id="issuer",
        name="issuer",
        display_name="发文机关",
        type="string",
        required=True,
    )

    suggestion = LLMFallbackService().suggest_mapping(
        task_id="task_llm_badcase",
        field=field,
        candidates=[candidate],
        used_source_paths=set(),
        badcases=[
            {
                "source_field": "责任主体",
                "forbidden_target_fields": ["issuer"],
            }
        ],
    )

    assert suggestion is None


def test_openai_compatible_llm_missing_config_degrades_to_review_required():
    from app.config import Settings
    from app.schemas.mapping import FieldCandidate
    from app.schemas.target_schema import TargetField
    from app.services.llm_fallback_service import LLMFallbackService

    candidate = FieldCandidate(
        candidate_id="cand_unknown",
        task_id="task_llm_missing_key",
        doc_id="doc_llm",
        source_path="$.metadata.unknown_source",
        source_name="unknown_source",
        value_sample="needs review",
        inferred_type="string",
        confidence=0.5,
    )
    field = TargetField(
        field_id="issuer",
        name="issuer",
        display_name="Issuer",
        type="string",
        required=True,
    )
    service = LLMFallbackService(
        Settings(
            llm_fallback_enabled=True,
            llm_mode="openai_compatible",
            llm_api_key="super-secret",
            llm_base_url="",
            _env_file=None,
        )
    )

    suggestion = service.suggest_mapping(
        task_id="task_llm_missing_key",
        field=field,
        candidates=[candidate],
        used_source_paths=set(),
    )

    assert suggestion is not None
    assert suggestion.status == "review_required"
    assert suggestion.need_review is True
    assert any("error_code=missing_credentials" in item for item in suggestion.evidence)
    assert "super-secret" not in " ".join(suggestion.evidence)


def test_llm_fallback_badcase_filter_prevents_adapter_call():
    from app.schemas.mapping import FieldCandidate
    from app.schemas.target_schema import TargetField
    from app.services.llm_fallback_service import LLMFallbackRequest, LLMFallbackService

    class SpyAdapter:
        enabled = True
        model = "spy"

        def __init__(self) -> None:
            self.calls = 0

        def suggest(self, request: LLMFallbackRequest):
            self.calls += 1
            return None

    candidate = FieldCandidate(
        candidate_id="cand_forbidden",
        task_id="task_llm_no_call",
        doc_id="doc_llm",
        source_path="$.metadata.forbidden_source",
        source_name="forbidden_source",
        value_sample="forbidden",
        inferred_type="string",
        confidence=0.5,
    )
    field = TargetField(
        field_id="issuer",
        name="issuer",
        display_name="Issuer",
        type="string",
        required=True,
    )
    adapter = SpyAdapter()
    service = LLMFallbackService(adapter=adapter)

    suggestion = service.suggest_mapping(
        task_id="task_llm_no_call",
        field=field,
        candidates=[candidate],
        used_source_paths=set(),
        badcases=[
            {
                "source_field": "forbidden_source",
                "forbidden_target_fields": ["issuer"],
            }
        ],
    )

    assert suggestion is None
    assert adapter.calls == 0


def test_openai_compatible_llm_request_failure_degrades_to_review_required(monkeypatch):
    import urllib.error

    from app.config import Settings
    from app.schemas.mapping import FieldCandidate
    from app.schemas.target_schema import TargetField
    from app.services.llm_fallback_service import LLMFallbackService

    def fail_urlopen(*args, **kwargs):
        raise urllib.error.URLError("network unavailable")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
    candidate = FieldCandidate(
        candidate_id="cand_network",
        task_id="task_llm_network",
        doc_id="doc_llm",
        source_path="$.metadata.network_source",
        source_name="network_source",
        value_sample="needs review",
        inferred_type="string",
        confidence=0.5,
    )
    field = TargetField(
        field_id="issuer",
        name="issuer",
        display_name="Issuer",
        type="string",
        required=True,
    )
    service = LLMFallbackService(
        Settings(
            llm_fallback_enabled=True,
            llm_mode="openai_compatible",
            llm_api_key="super-secret",
            llm_base_url="https://llm.example/v1",
            llm_timeout_seconds=0.1,
            _env_file=None,
        )
    )

    suggestion = service.suggest_mapping(
        task_id="task_llm_network",
        field=field,
        candidates=[candidate],
        used_source_paths=set(),
    )

    assert suggestion is not None
    assert suggestion.status == "review_required"
    assert any("error_code=request_failed" in item for item in suggestion.evidence)
    assert "super-secret" not in " ".join(suggestion.evidence)
