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


def run_mapping(task_id: str, uir_name: str, schema_id: str, template_id: str, template=None):
    from app.services.candidate_service import CandidateService
    from app.services.mapping_service import MappingService
    from app.services.schema_service import SchemaService
    from app.services.template_service import TemplateService

    uir = load_uir(uir_name)
    schema = SchemaService(SCHEMAS_DIR).load_schema(schema_id)
    if template is None:
        template = TemplateService(TEMPLATES_DIR).load_template(template_id)
    candidates = CandidateService().extract_candidates(task_id, uir)
    return MappingService().map_fields(task_id, uir, schema, template, candidates)


def test_review_records_generate_active_knowledge_pack_for_effective_template():
    from app.services.effective_template_service import EffectiveTemplateService
    from app.services.knowledge_service import KnowledgeService
    from app.services.review_service import ReviewService
    from app.services.template_service import TemplateService

    base_template = TemplateService(TEMPLATES_DIR).load_template("policy_doc_base_v1")
    mapping_report = run_mapping(
        "task_policy_002",
        "policy/policy_002_alias_variants.json",
        "policy_doc",
        "policy_doc_base_v1",
    )

    review_records = ReviewService().approve_review_items(mapping_report, reviewer="eval")
    candidates = KnowledgeService().derive_candidates(
        review_records,
        mapping_report,
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
    )
    draft_pack = KnowledgeService().create_draft_pack(
        candidates,
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
    )

    draft_result = EffectiveTemplateService().resolve(base_template, [draft_pack])
    assert draft_result.applied_pack_ids == []
    assert "通知名称" not in draft_result.template.aliases.get("title", [])

    active_pack = KnowledgeService().activate_pack(draft_pack)
    active_result = EffectiveTemplateService().resolve(base_template, [active_pack])

    assert active_result.applied_pack_ids == [active_pack.pack_id]
    assert "通知名称" in active_result.template.aliases["title"]

    remapped = run_mapping(
        "task_policy_002_active",
        "policy/policy_002_alias_variants.json",
        "policy_doc",
        "policy_doc_base_v1",
        template=active_result.template,
    )
    assert any(
        mapping["source_field"]["source_name"] == "通知名称"
        and mapping["target_field_id"] == "title"
        and mapping["status"] == "accepted"
        for mapping in remapped.mappings
    )


def test_knowledge_service_filters_badcase_forbidden_aliases():
    from app.schemas.reports import MappingReport
    from app.services.knowledge_service import KnowledgeService
    from app.services.review_service import ReviewService

    mapping_report = MappingReport(
        task_id="task_badcase",
        schema_id="policy_doc",
        summary={},
        review_required_items=[
            {
                "mapping_id": "map_bad_issuer",
                "task_id": "task_badcase",
                "candidate_id": "cand_bad_responsibility",
                "source_field": {
                    "source_path": "$.metadata.责任主体",
                    "source_name": "责任主体",
                },
                "target_field_id": "issuer",
                "target_field_name": "issuer",
                "method": "fuzzy",
                "confidence": 0.62,
                "status": "review_required",
                "need_review": True,
                "value_sample": "某单位",
                "source_blocks": [],
                "evidence": [],
            }
        ],
    )
    review_records = ReviewService().approve_review_items(mapping_report, reviewer="eval")

    candidates = KnowledgeService().derive_candidates(
        review_records,
        mapping_report,
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        badcases=[
            {
                "source_field": "责任主体",
                "forbidden_target_fields": ["issuer"],
            }
        ],
    )

    assert candidates == []
