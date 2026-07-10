from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.artifact_consistency import ArtifactConsistencyReport
from app.schemas.chunk_provider import ChunkProviderOptions, ChunkProviderResponse
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.document_summary import DocumentSummary, SummarySentenceTrace
from app.schemas.metadata_template import MetadataFieldConfig, MetadataTemplateConfig
from app.schemas.uir import UIRDocument, UIREntity


def test_legacy_metadata_template_fields_remain_valid() -> None:
    template = MetadataTemplateConfig.model_validate(
        {
            "template_id": "announcement_doc_base_v1",
            "schema_id": "announcement_doc",
            "version": "1.0.0",
            "metadata_fields": [
                {"field_id": "language", "required": False, "default": "zh-CN"}
            ],
        }
    )

    assert template.metadata_fields[0].type == "any"
    assert template.metadata_fields[0].default == "zh-CN"


@pytest.mark.parametrize(
    "source_path",
    [
        "environment.API_KEY",
        "uir.metadata..language",
        "uir.metadata[language]",
        "$.metadata.language",
        "system.__class__",
        "transformed_fields.title.upper()",
        "../uir.metadata.language",
    ],
)
def test_metadata_source_path_rejects_unsafe_or_unknown_syntax(source_path: str) -> None:
    with pytest.raises(ValidationError):
        MetadataFieldConfig(field_id="language", source_path=source_path)


@pytest.mark.parametrize(
    "source_path",
    [
        "uir.metadata.language",
        "transformed_fields.publish_date",
        "system.doc_id",
        "system.metadata_template_version",
    ],
)
def test_metadata_source_path_accepts_whitelisted_roots(source_path: str) -> None:
    field = MetadataFieldConfig(field_id="value", source_path=source_path)

    assert field.source_path == source_path


def test_system_source_path_rejects_unknown_system_value() -> None:
    with pytest.raises(ValidationError):
        MetadataFieldConfig(field_id="value", source_path="system.current_time")


def test_content_rules_reject_unknown_operator() -> None:
    with pytest.raises(ValidationError):
        ContentOrganizationOptions.model_validate(
            {
                "tag_rules": {
                    "content": {
                        "rules": [
                            {
                                "tag": "maintenance",
                                "contains_regex": ["maintenance"],
                            }
                        ]
                    }
                }
            }
        )


@pytest.mark.parametrize(
    "tag_template",
    ["language", "language:{value}:{value}", "language:{unknown}", "{value!r}"],
)
def test_management_tag_template_requires_one_plain_value_placeholder(
    tag_template: str,
) -> None:
    with pytest.raises(ValidationError):
        ContentOrganizationOptions.model_validate(
            {
                "tag_rules": {
                    "management": {
                        "metadata_rules": [
                            {
                                "tag_template": tag_template,
                                "source_path": "document_metadata.language",
                            }
                        ]
                    }
                }
            }
        )


def test_content_organization_accepts_strict_tag_summary_and_provider_config() -> None:
    options = ContentOrganizationOptions.model_validate(
        {
            "chunk_strategy": "source_block_aware",
            "target_tokens": 768,
            "min_tokens": 128,
            "max_tokens": 1024,
            "overlap_tokens": 80,
            "summary": {
                "chunk_mode": "deterministic",
                "document_mode": "extractive",
                "document_max_sentences": 5,
                "document_max_chars": 500,
            },
            "tag_rules": {
                "content": {
                    "base_tags": ["announcement"],
                    "rules": [
                        {"tag": "maintenance", "any_terms": ["maintenance"]}
                    ],
                },
                "management": {
                    "static_tags": ["domain:campus"],
                    "metadata_rules": [
                        {
                            "tag_template": "language:{value}",
                            "source_path": "document_metadata.language",
                        }
                    ],
                },
                "quality": {
                    "enabled_builtin_rules": ["source_linked", "validation_error"]
                },
            },
            "provider": "topic11",
            "fallback_to_internal": True,
            "strict_provider": False,
        }
    )

    assert options.summary.document_mode == "extractive"
    assert options.tag_rules.content.rules[0].tag == "maintenance"
    assert options.provider == "topic11"


def test_uir_entity_contract_preserves_upstream_identity() -> None:
    entity = UIREntity.model_validate(
        {
            "mention": "OpenAI",
            "canonical_name": "OpenAI",
            "entity_type": "organization",
            "normalized_id": "org:openai",
            "link_status": "linked",
            "confidence": 0.99,
            "source_block_ids": ["b1"],
            "source_agent": "topic7",
            "evidence": {"method": "upstream"},
        }
    )

    assert entity.normalized_id == "org:openai"
    assert entity.link_status == "linked"


def test_uir_entity_rejects_linked_status_without_normalized_id() -> None:
    with pytest.raises(ValidationError):
        UIREntity(mention="OpenAI", link_status="linked")


def test_legacy_uir_without_entities_remains_valid() -> None:
    uir = UIRDocument.model_validate(
        {"uir_version": "1.0", "doc_id": "doc-1", "blocks": []}
    )

    assert uir.entities == []


def test_document_summary_contract_carries_exact_sentence_trace() -> None:
    summary = DocumentSummary(
        text="Source sentence.",
        mode="extractive",
        source_block_ids=["b1"],
        source_chunk_ids=["c1"],
        sentence_traces=[
            SummarySentenceTrace(
                summary_sentence="Source sentence.",
                source_block_id="b1",
                source_text_span="Source sentence.",
            )
        ],
        char_count=16,
        generated_by="DocumentSummaryService",
        faithfulness_passed=True,
    )

    assert summary.sentence_traces[0].source_block_id == "b1"


def test_chunk_provider_contract_rejects_duplicate_chunk_ids() -> None:
    with pytest.raises(ValidationError):
        ChunkProviderResponse.model_validate(
            {
                "contract_version": "1.0",
                "provider": "topic11",
                "provider_version": "test",
                "chunks": [
                    {"chunk_id": "c1", "text": "one", "source_block_ids": ["b1"]},
                    {"chunk_id": "c1", "text": "two", "source_block_ids": ["b2"]},
                ],
            }
        )


def test_chunk_provider_options_are_deterministic_by_default() -> None:
    options = ChunkProviderOptions()

    assert options.provider == "internal"
    assert options.fallback_to_internal is True
    assert options.strict_provider is False


def test_artifact_consistency_report_requires_coverage_bounds() -> None:
    with pytest.raises(ValidationError):
        ArtifactConsistencyReport(
            passed=True,
            field_coverage=1.1,
            block_coverage=1.0,
            chunk_source_coverage=1.0,
            summary_consistent=True,
            metadata_consistent=True,
        )
