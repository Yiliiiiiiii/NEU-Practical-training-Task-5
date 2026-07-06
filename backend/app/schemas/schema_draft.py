from typing import Literal

from pydantic import Field

from app.schemas.common import StrictBaseModel
from app.schemas.uir import UIRDocument


class FieldCandidate(StrictBaseModel):
    field_name: str
    source_labels: list[str]
    value_examples: list[str] = Field(default_factory=list)
    frequency: float
    inferred_type: Literal["string", "date", "amount", "identifier", "number", "boolean"]
    evidence_paths: list[str]
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float
    review_required: bool = False


class FieldDiscoveryResult(StrictBaseModel):
    sample_count: int
    field_candidates: list[FieldCandidate]
    warnings: list[str] = Field(default_factory=list)
    llm_auto_accepted_count: int = 0


class DraftSchemaField(StrictBaseModel):
    field_id: str
    name: str
    display_name: str
    type: str
    required_recommended: bool = False
    description: str
    source_evidence: list[str]
    evidence_paths: list[str]
    confidence: float
    review_required: bool = False
    risk_flags: list[str] = Field(default_factory=list)


class DraftSchema(StrictBaseModel):
    schema_id: str
    name: str
    version: str = "0.1.0-draft"
    status: Literal["draft"] = "draft"
    sample_count: int
    fields: list[DraftSchemaField]
    must_not_auto_activate: bool = True


class TemplateDraftRule(StrictBaseModel):
    target_field: str
    aliases: list[str]
    confidence: float
    evidence_count: int
    evidence_paths: list[str]
    review_required: bool = False
    risk_flags: list[str] = Field(default_factory=list)


class RegexDraftSuggestion(StrictBaseModel):
    target_field: str
    pattern: str
    positive_examples: list[str] = Field(default_factory=list)
    negative_examples: list[str] = Field(default_factory=list)
    review_required: bool = True


class DraftTemplate(StrictBaseModel):
    template_id: str
    schema_id: str
    name: str
    version: str = "0.1.0-draft"
    status: Literal["draft"] = "draft"
    alias_rules: list[TemplateDraftRule] = Field(default_factory=list)
    regex_suggestions: list[RegexDraftSuggestion] = Field(default_factory=list)
    must_not_auto_activate: bool = True


class DraftRiskItem(StrictBaseModel):
    risk_type: str
    source_label: str | None = None
    target_field: str | None = None
    severity: Literal["low", "medium", "high"]
    action: str


class DraftRiskReport(StrictBaseModel):
    must_not_auto_activate: bool = True
    risk_count: int
    risks: list[DraftRiskItem] = Field(default_factory=list)
    badcase_violations: int = 0
    llm_auto_accepted_count: int = 0


class SchemaDraftDiscoverRequest(StrictBaseModel):
    documents: list[UIRDocument] = Field(min_length=1, max_length=50)


class SchemaDraftGenerateRequest(StrictBaseModel):
    documents: list[UIRDocument] = Field(min_length=1, max_length=50)
    schema_id: str
    schema_name: str
    template_id: str


class SchemaDraftReport(StrictBaseModel):
    sample_count: int
    candidate_count: int
    source_doc_ids: list[str]
    deterministic: bool = True
    must_not_auto_activate: bool = True
    risk_count: int
    badcase_violations: int = 0
    llm_auto_accepted_count: int = 0
    secret_leak_count: int = 0


class SchemaDraftPackage(StrictBaseModel):
    draft_id: str
    created_at: str
    status: Literal["draft"] = "draft"
    discovery: FieldDiscoveryResult
    draft_schema: DraftSchema
    draft_template: DraftTemplate
    risk_report: DraftRiskReport
    draft_report: SchemaDraftReport
    must_not_auto_activate: bool = True


class SchemaDraftExportResponse(StrictBaseModel):
    draft_id: str
    files: dict[str, str]
    sha256: dict[str, str]
    must_not_auto_activate: bool = True
