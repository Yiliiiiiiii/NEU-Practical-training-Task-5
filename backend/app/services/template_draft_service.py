from app.schemas.schema_draft import (
    DraftTemplate,
    FieldDiscoveryResult,
    TemplateDraftRule,
)


class TemplateDraftService:
    def generate(
        self,
        discovery: FieldDiscoveryResult,
        *,
        schema_id: str,
        template_id: str,
    ) -> DraftTemplate:
        rules = [
            TemplateDraftRule(
                target_field=candidate.field_name,
                aliases=candidate.source_labels,
                confidence=candidate.confidence,
                evidence_count=len(candidate.evidence_paths),
                evidence_paths=candidate.evidence_paths,
                review_required=candidate.review_required,
                risk_flags=candidate.risk_flags,
            )
            for candidate in discovery.field_candidates
        ]
        return DraftTemplate(
            template_id=template_id,
            schema_id=schema_id,
            name=f"{schema_id} Draft Template",
            alias_rules=rules,
            regex_suggestions=[],
            must_not_auto_activate=True,
        )
