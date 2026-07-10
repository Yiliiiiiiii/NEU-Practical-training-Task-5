import pytest
from pydantic import ValidationError

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.content_organization import ContentOrganizationOptions
from app.schemas.reports import MappingReport, ReportIssue, ValidationReport
from app.schemas.target_schema import TargetSchema
from app.services.chunk_organizer_service import ChunkOrganizerService


def make_schema() -> TargetSchema:
    return TargetSchema.model_validate(
        {
            "schema_id": "policy_doc",
            "name": "Policy",
            "version": "1.0.0",
            "fields": [
                {
                    "field_id": "title",
                    "name": "title",
                    "display_name": "标题",
                    "type": "string",
                    "required": True,
                },
                {
                    "field_id": "issuer",
                    "name": "issuer",
                    "display_name": "发文机关",
                    "type": "string",
                    "required": True,
                },
            ],
            "json_schema": {"type": "object"},
        }
    )


def make_canonical() -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task_policy",
        doc_id="doc_policy",
        schema_id="policy_doc",
        doc_meta={
            "metadata": {"issuer": "市数据管理局"},
            "entities": [
                {
                    "mention": "市数据管理局",
                    "canonical_name": "市数据管理局",
                    "entity_type": "organization",
                    "normalized_id": "org:city-data-office",
                    "link_status": "linked",
                    "confidence": 1.0,
                    "source_block_ids": ["blk_001"],
                    "source_agent": "fixture",
                    "evidence": {},
                }
            ],
        },
        fields={
            "issuer": CanonicalField(
                value="市数据管理局",
                type="string",
                source_candidates=["cand_issuer"],
                source_blocks=["blk_001"],
            )
        },
        blocks=[
            CanonicalBlock(
                block_id="blk_001",
                type="paragraph",
                level=None,
                text="本制度适用于市级数据资源管理，责任部门应当按流程执行。",
                source_blocks=["blk_001"],
                source_anchor={"page": 2, "bbox": [1.0, 2.0, 3.0, 4.0]},
                text_hash="sha256:abc",
            )
        ],
        assets=[],
    )


def make_structured_canonical() -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task_structured",
        doc_id="doc_structured",
        schema_id="policy_doc",
        doc_meta={"metadata": {"issuer": "Data Office"}},
        fields={},
        blocks=[
            CanonicalBlock(
                block_id="head_1",
                type="heading",
                level=1,
                text="Policy Overview",
                source_blocks=["head_1"],
                source_anchor={"page": 1},
            ),
            CanonicalBlock(
                block_id="para_1",
                type="paragraph",
                text=(
                    "This policy defines approval responsibilities. "
                    "Teams must follow the process."
                ),
                source_blocks=["para_1"],
                source_anchor={"page": 1},
            ),
            CanonicalBlock(
                block_id="table_1",
                type="table",
                text="\n".join(
                    [
                        "Name: Alpha",
                        "Owner: Operations",
                        "SLA: 24 hours",
                        "Escalation: Security review required before publication.",
                    ]
                ),
                source_blocks=["table_1"],
                source_anchor={"page": 2},
            ),
            CanonicalBlock(
                block_id="head_2",
                type="heading",
                level=2,
                text="Review Steps",
                source_blocks=["head_2"],
                source_anchor={"page": 3},
            ),
            CanonicalBlock(
                block_id="para_2",
                type="paragraph",
                text="Submit draft. Review evidence. Publish approved version.",
                source_blocks=["para_2"],
                source_anchor={"page": 3},
            ),
        ],
        assets=[],
    )


def make_mapping_report(review_required: bool = False) -> MappingReport:
    return MappingReport(
        task_id="task_policy",
        schema_id="policy_doc",
        summary={"review_required": 1 if review_required else 0},
        mappings=[],
        unmapped=[],
        review_required_items=[{"target_field_id": "issuer"}] if review_required else [],
    )


def test_empty_chunks_return_report_warning():
    chunks, report = ChunkOrganizerService().organize_chunks(
        chunks=[],
        canonical_model=make_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(),
        validation_report=None,
        task_id="task_policy",
        doc_id="doc_policy",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
    )

    assert chunks == []
    assert report.chunk_count == 0
    assert report.warnings == ["no_chunks_to_organize"]


def test_organizer_adds_summary_keywords_tags_links_and_entities_stably():
    service = ChunkOrganizerService()
    base_chunks = [
        {
            "chunk_id": "chunk_doc_policy_blk_001_1",
            "text": "本制度适用于市级数据资源管理，责任部门应当按流程执行。",
            "source_block_ids": ["blk_001"],
            "title_path": ["第一章 总则"],
        }
    ]
    validation_report = ValidationReport(
        task_id="task_policy",
        schema_id="policy_doc",
        passed=False,
        summary={"error_count": 1},
        issues=[
            ReportIssue(
                level="error",
                message="Required field is missing.",
                field_id="title",
                code="required_field_missing",
            )
        ],
    )
    options = ContentOrganizationOptions(
        chunk_strategy="source_block_aware",
        min_tokens=1,
        target_tokens=1200,
        max_tokens=1400,
        overlap_tokens=0,
        tag_rules={
            "content": {
                "base_tags": ["policy"],
                "rules": [
                    {"tag": "scope", "any_terms": ["适用", "范围", "对象"]},
                    {
                        "tag": "responsibility",
                        "any_terms": ["责任", "部门", "负责"],
                    },
                ],
            },
            "management": {"static_tags": ["domain:governance"]},
        },
    )

    first_chunks, first_report = service.organize_chunks(
        chunks=base_chunks,
        canonical_model=make_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(review_required=True),
        validation_report=validation_report,
        task_id="task_policy",
        doc_id="doc_policy",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        template_version="1.0.0",
        options=options,
    )
    second_chunks, second_report = service.organize_chunks(
        chunks=base_chunks,
        canonical_model=make_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(review_required=True),
        validation_report=validation_report,
        task_id="task_policy",
        doc_id="doc_policy",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        template_version="1.0.0",
        options=options,
    )

    chunk = first_chunks[0]
    assert first_chunks == second_chunks
    assert first_report.model_dump(mode="json") == second_report.model_dump(mode="json")
    assert chunk["summary"]
    assert chunk["keywords"]
    assert {"policy", "scope", "responsibility"}.issubset(set(chunk["tags"]["content"]))
    assert "validation_error" not in chunk["tags"]["quality"]
    assert "mapping_review_required" in chunk["tags"]["quality"]
    assert first_report.document_quality_flags[0]["tag"] == "validation_error"
    assert chunk["source_links"][0]["block_id"] == "blk_001"
    assert chunk["source_links"][0]["page_no"] == 2
    assert chunk["entity_tags"][0]["text"] == "市数据管理局"
    assert first_report.chunks_with_summary == 1
    assert first_report.chunks_with_keywords == 1
    assert first_report.chunks_with_source_links == 1


def test_chunk_options_defaults_are_backward_compatible():
    options = ContentOrganizationOptions()

    assert options.chunk_strategy == "heading_aware"
    assert options.target_tokens == 768
    assert options.min_tokens == 128
    assert options.max_tokens == 1024
    assert options.overlap_tokens == 80
    assert options.protect_tables is True
    assert options.protect_lists is True
    assert options.protect_code_blocks is True
    assert options.enable_parent_child is False


def test_chunk_options_reject_invalid_token_ranges():
    with pytest.raises(ValidationError):
        ContentOrganizationOptions(min_tokens=200, target_tokens=100, max_tokens=300)

    with pytest.raises(ValidationError):
        ContentOrganizationOptions(target_tokens=128, overlap_tokens=128)


def test_heading_aware_chunks_preserve_title_path():
    chunks, report = ChunkOrganizerService().organize_chunks(
        chunks=[],
        canonical_model=make_structured_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(),
        validation_report=None,
        task_id="task_structured",
        doc_id="doc_structured",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        options=ContentOrganizationOptions(
            chunk_strategy="heading_aware",
            min_tokens=1,
            target_tokens=12,
            max_tokens=28,
            overlap_tokens=0,
        ),
    )

    assert chunks
    assert any(chunk["title_path"] == ["Policy Overview"] for chunk in chunks)
    assert any(chunk["title_path"] == ["Policy Overview", "Review Steps"] for chunk in chunks)
    assert report.summary["strategy"] == "heading_aware"
    assert report.summary["chunk_count"] == len(chunks)
    assert report.summary["source_linked_count"] == len(chunks)


def test_table_blocks_are_not_split():
    chunks, report = ChunkOrganizerService().organize_chunks(
        chunks=[],
        canonical_model=make_structured_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(),
        validation_report=None,
        task_id="task_structured",
        doc_id="doc_structured",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        options=ContentOrganizationOptions(
            chunk_strategy="table_protect",
            min_tokens=1,
            target_tokens=8,
            max_tokens=12,
            overlap_tokens=0,
            protect_tables=True,
        ),
    )

    table_chunks = [
        chunk for chunk in chunks if "table_1" in chunk.get("source_block_ids", [])
    ]
    assert len(table_chunks) == 1
    assert "Escalation: Security review required before publication." in table_chunks[0]["text"]
    assert table_chunks[0]["organization_trace"]["protected_blocks"] == ["table_1"]
    assert report.summary["protected_blocks_count"] == 1


def test_oversized_protected_block_gets_quality_flag():
    chunks, report = ChunkOrganizerService().organize_chunks(
        chunks=[],
        canonical_model=make_structured_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(),
        validation_report=None,
        task_id="task_structured",
        doc_id="doc_structured",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        options=ContentOrganizationOptions(
            chunk_strategy="table_protect",
            min_tokens=1,
            target_tokens=4,
            max_tokens=5,
            overlap_tokens=0,
            protect_tables=True,
        ),
    )

    table_chunk = next(chunk for chunk in chunks if "table_1" in chunk["source_block_ids"])
    assert "oversized_protected_block" in table_chunk["quality_flags"]
    assert "oversized_protected_block" in table_chunk["tags"]["quality"]
    assert report.summary["oversized_protected_blocks_count"] == 1
    assert report.summary["quality_flags_summary"]["oversized_protected_block"] == 1


def test_parent_child_chunks_have_parent_ids():
    chunks, report = ChunkOrganizerService().organize_chunks(
        chunks=[],
        canonical_model=make_structured_canonical(),
        schema=make_schema(),
        mapping_report=make_mapping_report(),
        validation_report=None,
        task_id="task_structured",
        doc_id="doc_structured",
        schema_id="policy_doc",
        template_id="policy_doc_base_v1",
        options=ContentOrganizationOptions(
            chunk_strategy="parent_child",
            min_tokens=1,
            target_tokens=12,
            max_tokens=28,
            overlap_tokens=0,
            enable_parent_child=True,
        ),
    )

    parent_chunks = [chunk for chunk in chunks if chunk["granularity"] == "parent"]
    child_chunks = [chunk for chunk in chunks if chunk["granularity"] == "child"]
    parent_ids = {chunk["chunk_id"] for chunk in parent_chunks}
    assert parent_chunks
    assert child_chunks
    assert all(chunk["parent_chunk_id"] in parent_ids for chunk in child_chunks)
    assert report.summary["parent_chunk_count"] == len(parent_chunks)
    assert report.summary["child_chunk_count"] == len(child_chunks)
