import re
from typing import Any, Literal

from pydantic import (
    Field,
    PrivateAttr,
    field_validator,
    model_serializer,
    model_validator,
)

from app.schemas.common import StrictBaseModel


class SourceLink(StrictBaseModel):
    block_id: str
    source_path: str | None = None
    page_no: int | None = None
    bbox: list[float] | None = None
    anchor_text: str | None = None


class EntityTag(StrictBaseModel):
    text: str
    mention: str | None = None
    canonical_name: str | None = None
    entity_type: str = "unknown"
    normalized_id: str | None = None
    link_status: Literal["linked", "unlinked", "nil"] = "unlinked"
    source: Literal[
        "upstream", "schema_field", "metadata", "rule", "placeholder"
    ] = "placeholder"
    confidence: float | None = Field(default=1.0, ge=0.0, le=1.0)
    source_block_ids: list[str] = Field(default_factory=list)
    source_agent: str | None = None

    @model_validator(mode="after")
    def default_mention(self) -> "EntityTag":
        if self.mention is None:
            self.mention = self.text
        return self


class ChunkTags(StrictBaseModel):
    content: list[str] = Field(default_factory=list)
    management: list[str] = Field(default_factory=list)
    quality: list[str] = Field(default_factory=list)


class SummaryConfig(StrictBaseModel):
    chunk_mode: Literal["none", "deterministic"] = "deterministic"
    document_mode: Literal["none", "deterministic", "extractive"] = "extractive"
    document_max_sentences: int = Field(default=5, ge=1, le=50)
    document_max_chars: int = Field(default=500, ge=1, le=20_000)


class ContentTagRule(StrictBaseModel):
    rule_id: str | None = None
    tag: str = Field(min_length=1)
    any_terms: list[str] = Field(default_factory=list)
    all_terms: list[str] = Field(default_factory=list)
    none_terms: list[str] = Field(default_factory=list)
    title_terms: list[str] = Field(default_factory=list)
    block_types: list[str] = Field(default_factory=list)
    case_sensitive: bool = False

    @model_validator(mode="after")
    def validate_predicate(self) -> "ContentTagRule":
        if not any(
            (
                self.any_terms,
                self.all_terms,
                self.none_terms,
                self.title_terms,
                self.block_types,
            )
        ):
            raise ValueError("content tag rule requires at least one predicate")
        return self


class ContentTagRules(StrictBaseModel):
    base_tags: list[str] = Field(default_factory=list)
    rules: list[ContentTagRule] = Field(default_factory=list)


class ManagementMetadataRule(StrictBaseModel):
    rule_id: str | None = None
    tag_template: str
    source_path: str
    omit_if_missing: bool = True

    @field_validator("tag_template")
    @classmethod
    def validate_tag_template(cls, value: str) -> str:
        if value.count("{value}") != 1:
            raise ValueError("tag_template must contain exactly one {value} placeholder")
        remainder = value.replace("{value}", "")
        if "{" in remainder or "}" in remainder:
            raise ValueError("tag_template contains an unsupported placeholder")
        return value

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        if not re.fullmatch(
            r"(?:document_metadata|schema|package)\.[A-Za-z][A-Za-z0-9_-]*"
            r"(?:\.[A-Za-z][A-Za-z0-9_-]*)*",
            value,
        ):
            raise ValueError("management source_path must use a whitelisted root")
        return value


class ManagementTagRules(StrictBaseModel):
    static_tags: list[str] = Field(default_factory=list)
    metadata_rules: list[ManagementMetadataRule] = Field(default_factory=list)


QualityRuleName = Literal[
    "source_linked",
    "anchor_linked",
    "length_ok",
    "summarized",
    "keyworded",
    "entity_linked",
    "empty_text",
    "short_chunk",
    "overlong_chunk",
    "oversized_protected_block",
    "summary_missing",
    "keyword_missing",
    "source_unlinked",
    "mapping_review_required",
    "validation_error",
    "entity_unlinked",
]


class QualityTagRules(StrictBaseModel):
    enabled_builtin_rules: list[QualityRuleName] = Field(
        default_factory=lambda: [
            "source_linked",
            "anchor_linked",
            "length_ok",
            "summarized",
            "keyworded",
            "entity_linked",
            "empty_text",
            "short_chunk",
            "overlong_chunk",
            "oversized_protected_block",
            "summary_missing",
            "keyword_missing",
            "source_unlinked",
            "mapping_review_required",
            "validation_error",
            "entity_unlinked",
        ]
    )


class TagRules(StrictBaseModel):
    content: ContentTagRules = Field(default_factory=ContentTagRules)
    management: ManagementTagRules = Field(default_factory=ManagementTagRules)
    quality: QualityTagRules = Field(default_factory=QualityTagRules)


class BlockExclusion(StrictBaseModel):
    block_id: str = Field(min_length=1)
    exclusion_reason: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)


class ContentOrganizationOptions(StrictBaseModel):
    _legacy_summary_mode_used: bool = PrivateAttr(default=False)

    chunk_strategy: Literal[
        "fixed_window",
        "heading_aware",
        "source_block_aware",
        "table_protect",
        "parent_child",
    ] = "heading_aware"
    target_tokens: int = Field(default=768, gt=0)
    min_tokens: int = Field(default=128, gt=0)
    max_tokens: int = Field(default=1024, gt=0)
    overlap_tokens: int = Field(default=80, ge=0)
    protect_tables: bool = True
    protect_lists: bool = True
    protect_code_blocks: bool = True
    enable_parent_child: bool = False
    enable_light_semantic_boundary: bool = True
    legacy_summary_mode_input: Literal["none", "deterministic"] = Field(
        default="deterministic",
        validation_alias="summary_mode",
        exclude=True,
        deprecated=True,
        repr=False,
        title="Summary Mode",
    )
    keyword_mode: Literal["none", "deterministic"] = "deterministic"
    summary: SummaryConfig = Field(default_factory=SummaryConfig)
    tag_rules: TagRules = Field(default_factory=TagRules)
    provider: Literal["internal", "topic11"] = "internal"
    fallback_to_internal: bool = True
    strict_provider: bool = False
    enable_legacy_entity_inference: bool = False
    block_exclusions: list[BlockExclusion] = Field(default_factory=list)

    @model_validator(mode="wrap")
    @classmethod
    def migrate_legacy_summary_mode(cls, value: Any, handler):
        if isinstance(value, cls):
            return handler(value)
        if not isinstance(value, dict) or "summary_mode" not in value:
            return handler(value)

        payload = dict(value)
        legacy_mode = payload["summary_mode"]
        raw_summary = payload.get("summary")
        if isinstance(raw_summary, SummaryConfig):
            nested_mode_is_explicit = "chunk_mode" in raw_summary.model_fields_set
            nested_mode = raw_summary.chunk_mode
        elif isinstance(raw_summary, dict):
            nested_mode_is_explicit = "chunk_mode" in raw_summary
            nested_mode = raw_summary.get("chunk_mode")
        else:
            nested_mode_is_explicit = False
            nested_mode = None

        if nested_mode_is_explicit and nested_mode != legacy_mode:
            raise ValueError(
                "summary_mode conflicts with explicitly supplied summary.chunk_mode"
            )
        if not nested_mode_is_explicit:
            if isinstance(raw_summary, SummaryConfig):
                payload["summary"] = raw_summary.model_copy(
                    update={"chunk_mode": legacy_mode}
                )
            elif raw_summary is None and "summary" in payload:
                return handler(payload)
            else:
                nested_summary = dict(raw_summary or {})
                nested_summary["chunk_mode"] = legacy_mode
                payload["summary"] = nested_summary
        result = handler(payload)
        result._legacy_summary_mode_used = True
        return result

    @model_validator(mode="after")
    def validate_token_window(self):
        if self.max_tokens < self.min_tokens:
            raise ValueError("max_tokens must be greater than or equal to min_tokens")
        if not self.min_tokens <= self.target_tokens <= self.max_tokens:
            raise ValueError("target_tokens must be between min_tokens and max_tokens")
        if self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be less than target_tokens")
        return self

    @property
    def legacy_summary_mode_used(self) -> bool:
        return self._legacy_summary_mode_used

    @property
    def summary_mode(self) -> Literal["none", "deterministic"]:
        return self.summary.chunk_mode

    @model_serializer(mode="wrap")
    def serialize_legacy_summary_mode(self, handler):
        payload = handler(self)
        payload.pop("summary_mode", None)
        if self._legacy_summary_mode_used:
            payload["summary_mode"] = self.summary.chunk_mode
        return payload


class OrganizedChunk(StrictBaseModel):
    chunk_id: str
    parent_chunk_id: str | None = None
    doc_id: str | None = None
    task_id: str | None = None
    index: int
    chunk_index: int | None = None
    strategy: str | None = None
    granularity: Literal["parent", "child"] | None = None
    text: str
    token_estimate: int
    char_count: int | None = None
    title: str | None = None
    title_path: list[str] = Field(default_factory=list)
    source_block_ids: list[str] = Field(default_factory=list)
    source_links: list[SourceLink] = Field(default_factory=list)
    content_tags: list[str] = Field(default_factory=list)
    management_tags: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    tags: ChunkTags = Field(default_factory=ChunkTags)
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    entity_tags: list[EntityTag] = Field(default_factory=list)
    created_by: str = "ChunkOrganizerService"
    organization_trace: dict[str, Any] = Field(default_factory=dict)


class ContentOrganizationReport(StrictBaseModel):
    task_id: str
    doc_id: str
    chunk_count: int
    chunks_with_summary: int
    chunks_with_keywords: int
    chunks_with_source_links: int
    chunks_with_content_tags: int
    chunks_with_quality_tags: int
    warnings: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    document_summary: dict[str, Any] | None = None
    document_quality_flags: list[dict[str, Any]] = Field(default_factory=list)
    provider_trace: dict[str, Any] = Field(default_factory=dict)
    tag_rule_summary: dict[str, Any] = Field(default_factory=dict)
