from __future__ import annotations

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.reports import MappingReport, ReportIssue, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.services.chunk_organizer_service import ChunkOrganizerService


def _schema(schema_id: str = "custom_doc") -> TargetSchema:
    return TargetSchema.model_validate(
        {
            "schema_id": schema_id,
            "name": "Custom",
            "version": "1.0.0",
            "fields": [
                {
                    "field_id": "field_a",
                    "name": "field_a",
                    "display_name": "Field A",
                    "type": "string",
                    "required": False,
                },
                {
                    "field_id": "field_b",
                    "name": "field_b",
                    "display_name": "Field B",
                    "type": "string",
                    "required": False,
                },
            ],
        }
    )


def _canonical(schema_id: str = "custom_doc") -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task-1",
        doc_id="doc-1",
        schema_id=schema_id,
        doc_meta={
            "source_metadata": {"source": "fixture"},
            "document_metadata": {"language": "zh-CN", "department": "IT"},
            "metadata": {"source": "fixture"},
        },
        fields={
            "field_a": CanonicalField(
                value="A", type="string", source_blocks=["block-a"]
            ),
            "field_b": CanonicalField(
                value="B", type="string", source_blocks=["block-b"]
            ),
        },
        blocks=[
            CanonicalBlock(
                block_id="block-a",
                type="paragraph",
                text="The platform maintenance starts tonight.",
                source_blocks=["block-a"],
            ),
            CanonicalBlock(
                block_id="block-b",
                type="paragraph",
                text="Normal service continues tomorrow.",
                source_blocks=["block-b"],
            ),
        ],
    )


def _chunks() -> list[dict]:
    return [
        {
            "chunk_id": "chunk-a",
            "text": "The platform maintenance starts tonight.",
            "source_block_ids": ["block-a"],
            "title_path": ["Operations"],
        },
        {
            "chunk_id": "chunk-b",
            "text": "Normal service continues tomorrow.",
            "source_block_ids": ["block-b"],
            "title_path": ["Operations"],
        },
    ]


def _mapping(*review_items: dict) -> MappingReport:
    return MappingReport(
        task_id="task-1",
        schema_id="custom_doc",
        summary={},
        mappings=[],
        unmapped=[],
        review_required_items=list(review_items),
    )


def _options() -> ContentOrganizationOptions:
    return ContentOrganizationOptions.model_validate(
        {
            "chunk_strategy": "source_block_aware",
            "target_tokens": 128,
            "min_tokens": 1,
            "max_tokens": 256,
            "overlap_tokens": 0,
            "tag_rules": {
                "content": {
                    "base_tags": ["announcement"],
                    "rules": [
                        {
                            "rule_id": "maintenance-term",
                            "tag": "maintenance",
                            "any_terms": ["maintenance", "system upgrade"],
                        }
                    ],
                },
                "management": {
                    "static_tags": ["domain:campus"],
                    "metadata_rules": [
                        {
                            "rule_id": "language-field",
                            "tag_template": "language:{value}",
                            "source_path": "document_metadata.language",
                        }
                    ],
                },
                "quality": {
                    "enabled_builtin_rules": [
                        "source_linked",
                        "anchor_linked",
                        "length_ok",
                        "summarized",
                        "keyworded",
                        "empty_text",
                        "short_chunk",
                        "overlong_chunk",
                        "mapping_review_required",
                        "validation_error",
                    ]
                },
            },
        }
    )


def _organize(
    *,
    mapping: MappingReport | None = None,
    validation: ValidationReport | None = None,
    options: ContentOrganizationOptions | None = None,
    schema_id: str = "custom_doc",
):
    return ChunkOrganizerService().organize_chunks(
        chunks=_chunks(),
        canonical_model=_canonical(schema_id),
        schema=_schema(schema_id),
        mapping_report=mapping or _mapping(),
        validation_report=validation,
        task_id="task-1",
        doc_id="doc-1",
        schema_id=schema_id,
        template_id="custom-v1",
        template_version="1.0.0",
        options=options or _options(),
    )


def test_new_schema_uses_content_rules_without_backend_edit() -> None:
    chunks, report = _organize()

    assert chunks[0]["content_tags"] == ["announcement", "maintenance"]
    assert chunks[1]["content_tags"] == ["announcement"]
    trace = chunks[0]["organization_trace"]["tag_traces"]
    assert any(
        item["tag"] == "maintenance" and item["rule_id"] == "maintenance-term"
        for item in trace
    )
    assert report.tag_rule_summary["content_rule_count"] == 1


def test_no_content_rules_yield_only_generic_schema_tag() -> None:
    options = ContentOrganizationOptions(
        chunk_strategy="source_block_aware",
        target_tokens=128,
        min_tokens=1,
        max_tokens=256,
        overlap_tokens=0,
    )

    chunks, _report = _organize(options=options, schema_id="policy_doc")

    assert all(chunk["content_tags"] == ["policy"] for chunk in chunks)


def test_management_tags_come_from_config_and_document_metadata_only() -> None:
    chunks, _report = _organize()

    for chunk in chunks:
        assert chunk["management_tags"] == ["domain:campus", "language:zh-CN"]
        assert not any(
            tag.startswith(("task:", "doc:", "chunk_index:"))
            for tag in chunk["management_tags"]
        )
    traces = chunks[0]["organization_trace"]["tag_traces"]
    assert any(
        item["tag"] == "language:zh-CN"
        and item["rule_id"] == "language-field"
        and item["related_field_ids"] == ["language"]
        for item in traces
    )


def test_missing_optional_management_metadata_omits_tag() -> None:
    canonical = _canonical()
    canonical.doc_meta["document_metadata"].pop("language")

    chunks, _report = ChunkOrganizerService().organize_chunks(
        chunks=_chunks(),
        canonical_model=canonical,
        schema=_schema(),
        mapping_report=_mapping(),
        validation_report=None,
        task_id="task-1",
        doc_id="doc-1",
        schema_id="custom_doc",
        template_id="custom-v1",
        options=_options(),
    )

    assert all(chunk["management_tags"] == ["domain:campus"] for chunk in chunks)


def test_mapping_review_tags_only_chunk_with_intersecting_source_blocks() -> None:
    chunks, report = _organize(
        mapping=_mapping(
            {
                "target_field_id": "field_a",
                "source_blocks": ["block-a"],
                "risk_flags": ["ambiguous_source"],
            }
        )
    )

    assert "mapping_review_required" in chunks[0]["quality_tags"]
    assert "mapping_review_required" not in chunks[1]["quality_tags"]
    assert report.document_quality_flags == []
    trace = next(
        item
        for item in chunks[0]["organization_trace"]["tag_traces"]
        if item["tag"] == "mapping_review_required"
    )
    assert trace["scope"] == "chunk"
    assert trace["source_block_ids"] == ["block-a"]
    assert trace["related_field_ids"] == ["field_a"]


def test_validation_error_tags_only_chunk_linked_to_field() -> None:
    validation = ValidationReport(
        task_id="task-1",
        schema_id="custom_doc",
        passed=False,
        summary={"error_count": 1},
        issues=[
            ReportIssue(
                level="error",
                message="Wrong type",
                field_id="field_b",
                code="field_type_invalid",
            )
        ],
    )

    chunks, report = _organize(validation=validation)

    assert "validation_error" not in chunks[0]["quality_tags"]
    assert "validation_error" in chunks[1]["quality_tags"]
    assert report.document_quality_flags == []


def test_unlocalizable_issue_is_document_flag_and_not_broadcast() -> None:
    validation = ValidationReport(
        task_id="task-1",
        schema_id="custom_doc",
        passed=False,
        summary={"error_count": 1},
        issues=[
            ReportIssue(
                level="error",
                message="Global metadata problem",
                stage="metadata_template",
                path="document_metadata.classification",
                code="metadata_required_missing",
            )
        ],
    )

    chunks, report = _organize(validation=validation)

    assert all("validation_error" not in chunk["quality_tags"] for chunk in chunks)
    assert report.document_quality_flags == [
        {
            "tag": "validation_error",
            "rule_id": "quality:validation_error",
            "scope": "document",
            "evidence": "Global metadata problem",
            "source_block_ids": [],
            "related_field_ids": [],
            "related_issue_codes": ["metadata_required_missing"],
        }
    ]


def test_tag_generation_and_traces_are_deterministic() -> None:
    first_chunks, first_report = _organize()
    second_chunks, second_report = _organize()

    assert first_chunks == second_chunks
    assert first_report == second_report


def test_backend_has_no_document_family_tag_table() -> None:
    assert not hasattr(ChunkOrganizerService, "CONTENT_TAG_RULES")
