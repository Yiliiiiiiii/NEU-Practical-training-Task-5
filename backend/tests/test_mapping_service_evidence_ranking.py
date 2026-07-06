from app.schemas.mapping import FieldCandidate
from app.schemas.mapping_template import MappingTemplate
from app.schemas.target_schema import TargetField, TargetSchema
from app.schemas.uir import UIRDocument
from app.services.mapping_service import MappingService


def make_uir() -> UIRDocument:
    return UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc-ranking",
            "metadata": {"domain": "general_doc"},
            "blocks": [
                {"block_id": "weak", "type": "paragraph", "text": "发布机构：某栏目"},
                {
                    "block_id": "strong",
                    "type": "paragraph",
                    "text": "服务对象：科技型中小企业",
                },
            ],
            "assets": [],
            "normalization_records": [],
        }
    )


def make_schema(
    field_id: str,
    field_type: str = "string",
    *,
    required: bool = False,
) -> TargetSchema:
    return TargetSchema(
        schema_id="general_doc",
        name="General document",
        version="1.0.0",
        fields=[
            TargetField(
                field_id=field_id,
                name=field_id,
                display_name=field_id,
                type=field_type,
                required=required,
            )
        ],
    )


def make_template(field_id: str, aliases: list[str]) -> MappingTemplate:
    return MappingTemplate(
        template_id="general_doc_base_v1",
        schema_id="general_doc",
        name="General",
        version="1.0.0",
        aliases={field_id: aliases},
    )


def candidate(
    *,
    candidate_id: str,
    source_name: str,
    source_path: str,
    value: str,
    target_hint: str | None,
    evidence_type: str,
    confidence: float,
    quality_flags: list[str] | None = None,
    source_blocks: list[str] | None = None,
) -> FieldCandidate:
    return FieldCandidate(
        candidate_id=candidate_id,
        task_id="task-ranking",
        doc_id="doc-ranking",
        source_path=source_path,
        source_name=source_name,
        display_name=source_name,
        value_sample=value,
        inferred_type="string",
        source_blocks=source_blocks or [],
        confidence=confidence,
        evidence=[f"extracted from {evidence_type}"],
        target_hints=[target_hint] if target_hint else [],
        evidence_type=evidence_type,
        confidence_hint=confidence,
        quality_flags=quality_flags or [],
    )


def test_high_evidence_service_object_candidate_wins_and_is_accepted() -> None:
    weak = candidate(
        candidate_id="weak",
        source_name="适用对象",
        source_path="$.metadata.page_column",
        value="办事群众",
        target_hint="service_object",
        evidence_type="page_column",
        confidence=0.62,
        quality_flags=["weak_evidence"],
    )
    strong = candidate(
        candidate_id="strong",
        source_name="service section evidence",
        source_path="$.blocks.strong.text",
        value="科技型中小企业",
        target_hint="service_object",
        evidence_type="service_object_section",
        confidence=0.9,
        source_blocks=["strong"],
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("service_object"),
        make_template("service_object", ["适用对象", "服务对象"]),
        [weak, strong],
    )

    assert report.review_required_items == []
    assert report.mappings[0]["candidate_id"] == "strong"
    assert report.mappings[0]["status"] == "accepted"
    trace = report.mappings[0]["ranking_trace"]
    assert trace["final_score"] >= 0.82
    assert set(trace) == {
        "label_score",
        "evidence_score",
        "context_score",
        "type_score",
        "source_quality_score",
        "risk_penalty",
        "final_score",
    }
    assert report.mappings[0]["rejected_candidates"][0]["candidate_id"] == "weak"


def test_high_evidence_application_conditions_candidate_is_accepted() -> None:
    conditions = candidate(
        candidate_id="conditions",
        source_name="申请条件",
        source_path="$.blocks.conditions.section",
        value="依法登记\n信用良好",
        target_hint="application_conditions",
        evidence_type="application_conditions_section",
        confidence=0.9,
        source_blocks=["conditions", "condition-list"],
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("application_conditions", "array[string]"),
        make_template("application_conditions", ["申请条件"]),
        [conditions],
    )

    assert report.mappings[0]["target_field_id"] == "application_conditions"
    assert report.mappings[0]["ranking_trace"]["final_score"] >= 0.82


def test_medium_page_publisher_issuer_stays_review_required() -> None:
    publisher = candidate(
        candidate_id="publisher",
        source_name="page_publisher.organization",
        source_path="$.blocks.weak.text#issuer",
        value="某栏目",
        target_hint="issuer",
        evidence_type="page_publisher_field",
        confidence=0.65,
        quality_flags=["medium_risk_issuer"],
        source_blocks=["weak"],
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("issuer", required=True),
        make_template("issuer", []),
        [publisher],
    )

    assert report.mappings == []
    assert report.review_required_items[0]["candidate_id"] == "publisher"
    assert report.review_required_items[0]["status"] == "review_required"
    assert "medium_risk_issuer" in report.review_required_items[0]["risk_flags"]
    assert report.unmapped == []


def test_alias_ranking_preserves_real_source_over_synthetic_alias() -> None:
    real = candidate(
        candidate_id="real-chair",
        source_name="林恒求主持",
        source_path="$.blocks.strong.text#chairperson",
        value="林恒求",
        target_hint=None,
        evidence_type="meeting_opening",
        confidence=0.9,
        source_blocks=["strong"],
    )
    synthetic = candidate(
        candidate_id="synthetic-chair",
        source_name="chairperson",
        source_path="$.blocks.strong.text#chairperson",
        value="林恒求",
        target_hint=None,
        evidence_type="meeting_opening_alias",
        confidence=0.9,
        source_blocks=["strong"],
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("chairperson"),
        make_template("chairperson", ["林恒求主持", "chairperson"]),
        [real, synthetic],
    )

    assert report.mappings[0]["candidate_id"] == "real-chair"


def test_unhinted_high_risk_metadata_does_not_create_fuzzy_review() -> None:
    retrieved = candidate(
        candidate_id="retrieved",
        source_name="retrieved_at",
        source_path="$.metadata.retrieved_at",
        value="2026-07-06T10:00:00Z",
        target_hint=None,
        evidence_type="metadata",
        confidence=0.8,
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("created_date", "date"),
        make_template("created_date", []),
        [retrieved],
    )

    assert report.mappings == []
    assert report.review_required_items == []


def test_traceable_paragraph_regex_document_number_is_accepted() -> None:
    document_number = candidate(
        candidate_id="doc-number",
        source_name="paragraph_regex.document_number",
        source_path="$.blocks.strong.text",
        value="国办函〔2025〕3号",
        target_hint=None,
        evidence_type="paragraph_regex",
        confidence=0.72,
        source_blocks=["strong"],
    )
    document_number.display_name = "document_number"

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        make_schema("document_number"),
        make_template("document_number", []),
        [document_number],
    )

    assert report.review_required_items == []
    assert report.mappings[0]["candidate_id"] == "doc-number"
    assert report.mappings[0]["method"] == "evidence_ranked"


def test_derived_publication_url_does_not_consume_source_provenance() -> None:
    schema = TargetSchema(
        schema_id="policy_doc",
        name="Policy",
        version="1.0.0",
        fields=[
            TargetField(
                field_id="publish_date",
                name="publish_date",
                display_name="publish_date",
                type="date",
            ),
            TargetField(
                field_id="source",
                name="source",
                display_name="source",
                type="string",
            ),
        ],
    )
    template = MappingTemplate(
        template_id="policy_doc_base_v1",
        schema_id="policy_doc",
        name="Policy",
        version="1.0.0",
        aliases={
            "publish_date": ["publish_date"],
            "source": ["source_url"],
        },
    )
    publication = candidate(
        candidate_id="publication",
        source_name="publish_date",
        source_path="$.metadata.source_url#publish_date",
        value="2025-11-06",
        target_hint="publish_date",
        evidence_type="official_attachment_url",
        confidence=0.9,
    )
    source = candidate(
        candidate_id="source",
        source_name="source_url",
        source_path="$.metadata.source_url",
        value="https://example.gov.cn/P020251106.pdf",
        target_hint="source",
        evidence_type="official_source_url",
        confidence=0.9,
    )

    report = MappingService().map_fields(
        "task-ranking",
        make_uir(),
        schema,
        template,
        [publication, source],
    )

    assert {item["target_field_id"] for item in report.mappings} == {
        "publish_date",
        "source",
    }
