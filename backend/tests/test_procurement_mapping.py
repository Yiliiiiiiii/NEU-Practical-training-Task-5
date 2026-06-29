import json
from pathlib import Path

from app.schemas.uir import UIRDocument
from app.services.candidate_service import CandidateService
from app.services.mapping_service import MappingService
from app.services.schema_service import SchemaService
from app.services.template_service import TemplateService

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_LIKE_DIR = ROOT / "examples" / "production_like"
SCHEMAS_DIR = PRODUCTION_LIKE_DIR / "schemas"
TEMPLATES_DIR = PRODUCTION_LIKE_DIR / "mapping_templates"


def procurement_catalog():
    schema = SchemaService(SCHEMAS_DIR).load_schema("procurement_doc", "1.0.0")
    template = TemplateService(TEMPLATES_DIR).load_template(
        "procurement_doc_base_v1",
        "1.0.0",
    )
    return schema, template


def procurement_uir(
    metadata: dict[str, object],
    *,
    doc_id: str = "procurement_test",
) -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": doc_id,
            "metadata": metadata,
            "blocks": [
                {
                    "block_id": f"{doc_id}_b001",
                    "type": "paragraph",
                    "text": "本公告内容以采购文件为准。",
                    "attributes": {},
                }
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def map_procurement(uir: UIRDocument, task_id: str = "task_procurement"):
    schema, template = procurement_catalog()
    candidates = CandidateService().extract_candidates(task_id, uir)
    report = MappingService().map_fields(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        candidates=candidates,
    )
    return schema, template, report


def test_procurement_aliases_map_project_budget_and_award_without_crossing() -> None:
    uir = procurement_uir(
        {
            "公告标题": "城市道路养护项目中标公告",
            "公告类型": "中标公告",
            "采购项目名称": "城市道路养护项目",
            "项目预算": "1,200,000元",
            "成交金额": "1,080,000元",
            "source_url": "https://example.gov.cn/procurement/1",
            "source_site": "example.gov.cn",
        }
    )

    _, _, report = map_procurement(uir)

    mappings = {item["target_field_id"]: item for item in report.mappings}
    assert mappings["project_name"]["source_field"]["source_name"] == "采购项目名称"
    assert mappings["budget_amount"]["source_field"]["source_name"] == "项目预算"
    assert mappings["winning_amount"]["source_field"]["source_name"] == "成交金额"
    assert mappings["budget_amount"]["source_path"] != mappings["winning_amount"]["source_path"]
    assert mappings["budget_amount"]["status"] == "accepted"
    assert mappings["winning_amount"]["status"] == "accepted"


def test_ambiguous_procurement_amounts_are_not_forced_into_accepted_mappings() -> None:
    uir = procurement_uir(
        {
            "公告标题": "采购结果公告",
            "公告类型": "结果公告",
            "项目名称": "办公设备采购",
            "金额一": "500000元",
            "金额二": "480000元",
            "source_url": "https://example.gov.cn/procurement/2",
            "source_site": "example.gov.cn",
        },
        doc_id="procurement_ambiguous",
    )

    _, _, report = map_procurement(uir, "task_procurement_ambiguous")

    accepted_amount_targets = {
        item["target_field_id"]
        for item in report.mappings
        if item["target_field_id"] in {"budget_amount", "winning_amount"}
    }
    ambiguous_reviews = [
        item
        for item in report.review_required_items
        if item["target_field_id"] in {"budget_amount", "winning_amount"}
    ]
    assert accepted_amount_targets == set()
    assert ambiguous_reviews
    assert all(item["status"] == "review_required" for item in ambiguous_reviews)
    assert all(item["confidence_tier"] != "high" for item in ambiguous_reviews)


def test_procurement_datetime_transform_validation_and_package_verification(
    tmp_path: Path,
) -> None:
    from app.services.canonical_service import CanonicalService
    from app.services.chunk_organizer_service import ChunkOrganizerService
    from app.services.package_service import PackageService
    from app.services.package_verifier_service import PackageVerifierService
    from app.services.render_service import RenderedArtifacts, RenderService
    from app.services.transform_service import TransformService
    from app.services.validation_service import ValidationService

    task_id = "task_procurement_package"
    uir = procurement_uir(
        {
            "公告标题": "城市道路养护项目采购公告",
            "公告类型": "采购公告",
            "项目名称": "城市道路养护项目",
            "项目编号": "CG-2026-001",
            "预算金额": "1,200,000元",
            "采购方式": "公开招标",
            "截止时间": "2026年7月15日 09:30",
            "source_url": "https://example.gov.cn/procurement/3",
            "source_site": "example.gov.cn",
        },
        doc_id="procurement_package",
    )
    schema, template, mapping_report = map_procurement(uir, task_id)

    transform_result = TransformService().transform(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )

    assert transform_result.data["notice_type"] == "procurement_notice"
    assert transform_result.data["procurement_method"] == "open_tender"
    assert transform_result.data["budget_amount"] == 1200000.0
    assert transform_result.data["deadline"] == "2026-07-15T09:30:00"
    assert transform_result.data["currency"] == "CNY"
    assert not transform_result.report["errors"]

    canonical = CanonicalService().build_canonical(
        task_id=task_id,
        uir=uir,
        schema=schema,
        template=template,
        transform_result=transform_result,
        mapping_report=mapping_report,
        execution_snapshot={"engine_version": "test"},
    )
    rendered = RenderService().render(canonical)
    preliminary_validation = ValidationService().validate(
        task_id=task_id,
        schema=schema,
        rendered=rendered,
    )
    organized_chunks, organization_report = ChunkOrganizerService().organize_chunks(
        chunks=rendered.chunks,
        canonical_model=canonical,
        schema=schema,
        mapping_report=mapping_report,
        validation_report=preliminary_validation,
        task_id=task_id,
        doc_id=uir.doc_id,
        schema_id=schema.schema_id,
        template_id=template.template_id,
        template_version=template.version,
    )
    rendered = RenderedArtifacts(
        structured_json=rendered.structured_json,
        markdown=rendered.markdown,
        chunks=organized_chunks,
    )
    validation_report = ValidationService().validate(
        task_id=task_id,
        schema=schema,
        rendered=rendered,
        require_content_organization=True,
    )

    assert validation_report.passed is True

    package_result = PackageService(tmp_path).create_package(
        task_id=task_id,
        doc_id=uir.doc_id,
        schema=schema,
        template=template,
        canonical=canonical,
        rendered=rendered,
        mapping_report=mapping_report,
        transform_report=transform_result.report,
        validation_report=validation_report,
        content_organization_report=organization_report,
    )
    package_dir = Path(package_result.metadata.zip_path).parent

    assert package_result.verifier_report.passed is True
    assert PackageVerifierService().verify_package(package_dir, strict=True).passed is True


def test_procurement_invalid_datetime_is_rejected_during_transform() -> None:
    from app.services.transform_service import TransformService

    uir = procurement_uir(
        {
            "公告标题": "无效截止时间采购公告",
            "公告类型": "采购公告",
            "项目名称": "无效截止时间测试",
            "截止时间": "下周三上午",
            "source_url": "https://example.gov.cn/procurement/4",
            "source_site": "example.gov.cn",
        },
        doc_id="procurement_invalid_datetime",
    )
    schema, template, mapping_report = map_procurement(
        uir,
        "task_procurement_invalid_datetime",
    )

    result = TransformService().transform(
        task_id="task_procurement_invalid_datetime",
        uir=uir,
        schema=schema,
        template=template,
        mapping_report=mapping_report,
    )

    assert "deadline" not in result.data
    assert any(
        error["field_id"] == "deadline" and error["code"] == "datetime_format_error"
        for error in result.report["errors"]
    )


def test_procurement_gold_cases_are_traceable_and_include_ambiguity_expectation() -> None:
    path = (
        PRODUCTION_LIKE_DIR
        / "expected"
        / "procurement_mapping_gold_cases.jsonl"
    )
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    traceable_cases = [case for case in cases if case.get("source_url")]
    assert traceable_cases
    assert all((ROOT / case["uir_file"]).is_file() for case in traceable_cases)
    assert any(
        case["expected_behavior"] == "review_required_or_low_confidence"
        for case in cases
    )
