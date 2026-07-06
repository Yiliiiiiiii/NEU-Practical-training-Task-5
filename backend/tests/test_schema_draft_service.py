from app.schemas.schema_draft import FieldCandidate, FieldDiscoveryResult
from app.services.schema_draft_service import SchemaDraftService


def discovery_result() -> FieldDiscoveryResult:
    return FieldDiscoveryResult(
        sample_count=5,
        field_candidates=[
            FieldCandidate(
                field_name="project_name",
                source_labels=["项目名称", "采购项目名称"],
                value_examples=["Project A", "Project B"],
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


def test_generates_evidence_backed_schema_draft_only() -> None:
    draft = SchemaDraftService().generate(
        discovery_result(),
        schema_id="project_notice_doc",
        name="Project Notice Draft",
    )

    assert draft.status == "draft"
    assert draft.must_not_auto_activate is True
    assert draft.version == "0.1.0-draft"
    assert all(field.source_evidence for field in draft.fields)
    assert all(field.evidence_paths for field in draft.fields)
    assert draft.fields[0].required_recommended is True
    assert draft.fields[1].review_required is True
