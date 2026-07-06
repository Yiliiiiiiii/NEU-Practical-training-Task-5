from app.schemas.schema_draft import FieldCandidate, FieldDiscoveryResult
from app.services.template_draft_service import TemplateDraftService


def test_generates_alias_rules_with_evidence_and_review_flags() -> None:
    discovery = FieldDiscoveryResult(
        sample_count=5,
        field_candidates=[
            FieldCandidate(
                field_name="project_name",
                source_labels=["项目名称", "采购项目名称"],
                value_examples=["Project A"],
                frequency=1.0,
                inferred_type="string",
                evidence_paths=["doc1.blocks[0].attributes.rows[0]"],
                confidence=0.95,
            ),
            FieldCandidate(
                field_name="budget_amount",
                source_labels=["预算金额"],
                value_examples=["100万元"],
                frequency=0.8,
                inferred_type="amount",
                evidence_paths=["doc1.blocks[0].attributes.rows[1]"],
                risk_flags=["budget_amount_not_award_amount"],
                confidence=0.86,
                review_required=True,
            ),
        ],
    )

    draft = TemplateDraftService().generate(
        discovery,
        schema_id="project_notice_doc",
        template_id="project_notice_doc_draft_v1",
    )

    assert draft.status == "draft"
    assert draft.must_not_auto_activate is True
    project_rule = next(rule for rule in draft.alias_rules if rule.target_field == "project_name")
    assert project_rule.aliases == ["项目名称", "采购项目名称"]
    assert project_rule.evidence_count == 1
    budget_rule = next(rule for rule in draft.alias_rules if rule.target_field == "budget_amount")
    assert budget_rule.review_required is True
