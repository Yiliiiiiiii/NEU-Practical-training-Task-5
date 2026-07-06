from app.schemas.schema_draft import (
    DraftSchema,
    DraftSchemaField,
    DraftTemplate,
    RegexDraftSuggestion,
    TemplateDraftRule,
)
from app.services.draft_risk_service import DraftRiskService


def test_risk_scan_blocks_forbidden_mapping_and_overbroad_regex() -> None:
    schema = DraftSchema(
        schema_id="unsafe_doc",
        name="Unsafe Draft",
        sample_count=5,
        fields=[
            DraftSchemaField(
                field_id="award_amount",
                name="award_amount",
                display_name="中标金额",
                type="amount",
                required_recommended=False,
                description="中标金额",
                source_evidence=["中标金额"],
                evidence_paths=["doc1.blocks[0].attributes.rows[0]"],
                confidence=0.9,
            )
        ],
    )
    template = DraftTemplate(
        template_id="unsafe_doc_draft_v1",
        schema_id="unsafe_doc",
        name="Unsafe Draft Template",
        alias_rules=[
            TemplateDraftRule(
                target_field="award_amount",
                aliases=["预算金额"],
                confidence=0.8,
                evidence_count=1,
                evidence_paths=["doc1.blocks[0].attributes.rows[1]"],
                review_required=True,
            )
        ],
        regex_suggestions=[
            RegexDraftSuggestion(
                target_field="award_amount",
                pattern=".*",
                positive_examples=["预算金额：100万元"],
                negative_examples=["中标金额：100万元"],
                review_required=True,
            )
        ],
    )

    report = DraftRiskService().scan(schema, template)

    assert report.must_not_auto_activate is True
    assert report.risk_count == 2
    assert {risk.risk_type for risk in report.risks} == {
        "forbidden_mapping",
        "overbroad_regex",
    }
    assert report.badcase_violations == 0
    assert report.llm_auto_accepted_count == 0
