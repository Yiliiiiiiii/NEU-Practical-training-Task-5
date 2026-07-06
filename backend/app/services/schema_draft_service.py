from app.schemas.schema_draft import (
    DraftSchema,
    DraftSchemaField,
    FieldDiscoveryResult,
)


class SchemaDraftService:
    def generate(
        self,
        discovery: FieldDiscoveryResult,
        *,
        schema_id: str,
        name: str,
    ) -> DraftSchema:
        if not schema_id.strip():
            raise ValueError("schema_id is required")
        fields = [
            DraftSchemaField(
                field_id=candidate.field_name,
                name=candidate.field_name,
                display_name=candidate.source_labels[0],
                type=candidate.inferred_type,
                required_recommended=candidate.frequency >= 0.8,
                description=candidate.source_labels[0],
                source_evidence=candidate.source_labels,
                evidence_paths=candidate.evidence_paths,
                confidence=candidate.confidence,
                review_required=candidate.review_required,
                risk_flags=candidate.risk_flags,
            )
            for candidate in discovery.field_candidates
        ]
        if not fields:
            raise ValueError("draft schema requires discovered fields")
        return DraftSchema(
            schema_id=schema_id,
            name=name,
            sample_count=discovery.sample_count,
            fields=fields,
            must_not_auto_activate=True,
        )
