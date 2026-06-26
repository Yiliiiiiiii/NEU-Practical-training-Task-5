from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
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
        doc_meta={"metadata": {"issuer": "市数据管理局"}},
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
    )

    chunk = first_chunks[0]
    assert first_chunks == second_chunks
    assert first_report.model_dump(mode="json") == second_report.model_dump(mode="json")
    assert chunk["summary"]
    assert chunk["keywords"]
    assert {"policy", "scope", "responsibility"}.issubset(set(chunk["tags"]["content"]))
    assert "validation_has_errors" in chunk["tags"]["quality"]
    assert "mapping_review_required" in chunk["tags"]["quality"]
    assert chunk["source_links"][0]["block_id"] == "blk_001"
    assert chunk["source_links"][0]["page_no"] == 2
    assert chunk["entity_tags"][0]["text"] == "市数据管理局"
    assert first_report.chunks_with_summary == 1
    assert first_report.chunks_with_keywords == 1
    assert first_report.chunks_with_source_links == 1
