from app.schemas.schema_draft import (
    DraftRiskItem,
    DraftRiskReport,
    DraftSchema,
    DraftTemplate,
)


class DraftRiskService:
    FORBIDDEN_PAIRS = {
        ("预算金额", "award_amount"),
        ("控制价", "award_amount"),
        ("主持人", "attendees"),
        ("联系人", "attendees"),
        ("成文日期", "publish_date"),
        ("retrieved_at", "effective_date"),
    }
    OVERBROAD_REGEX = {".*", ".+", "^.*$", "^.+$"}

    def scan(
        self,
        schema: DraftSchema,
        template: DraftTemplate,
    ) -> DraftRiskReport:
        risks: list[DraftRiskItem] = []
        schema_fields = {field.field_id for field in schema.fields}
        for field in schema.fields:
            if not field.source_evidence or not field.evidence_paths:
                risks.append(
                    DraftRiskItem(
                        risk_type="missing_source_evidence",
                        target_field=field.field_id,
                        severity="high",
                        action="add_evidence_or_remove",
                    )
                )
        for rule in template.alias_rules:
            if rule.target_field not in schema_fields:
                risks.append(
                    DraftRiskItem(
                        risk_type="hallucinated_target_field",
                        target_field=rule.target_field,
                        severity="high",
                        action="remove_or_review",
                    )
                )
            if not rule.evidence_paths:
                risks.append(
                    DraftRiskItem(
                        risk_type="missing_source_evidence",
                        target_field=rule.target_field,
                        severity="high",
                        action="add_evidence_or_remove",
                    )
                )
            for alias in rule.aliases:
                if (alias, rule.target_field) in self.FORBIDDEN_PAIRS:
                    risks.append(
                        DraftRiskItem(
                            risk_type="forbidden_mapping",
                            source_label=alias,
                            target_field=rule.target_field,
                            severity="high",
                            action="remove_or_review",
                        )
                    )
        for suggestion in template.regex_suggestions:
            if suggestion.pattern.strip() in self.OVERBROAD_REGEX:
                risks.append(
                    DraftRiskItem(
                        risk_type="overbroad_regex",
                        target_field=suggestion.target_field,
                        severity="high",
                        action="narrow_pattern_and_add_tests",
                    )
                )
        return DraftRiskReport(
            must_not_auto_activate=True,
            risk_count=len(risks),
            risks=risks,
            badcase_violations=0,
            llm_auto_accepted_count=0,
        )
