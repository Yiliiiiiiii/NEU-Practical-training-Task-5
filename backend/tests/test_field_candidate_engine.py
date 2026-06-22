from app.engines.field_candidate_engine import FieldCandidateEngine
from app.schemas.uir import UIRDocument


def test_extracts_candidates_from_metadata_blocks_and_tables():
    uir = UIRDocument.model_validate(
        {
            "uir_version": "1.0",
            "doc_id": "doc_test",
            "metadata": {"文档标题": "SchemaPack 手册"},
            "blocks": [
                {
                    "block_id": "heading_1",
                    "type": "heading",
                    "level": 1,
                    "text": "SchemaPack 手册",
                    "attributes": {"section_no": "1"},
                },
                {
                    "block_id": "paragraph_1",
                    "type": "paragraph",
                    "text": "发布日期：2026年6月22日。",
                    "attributes": {},
                },
                {
                    "block_id": "table_1",
                    "type": "table",
                    "attributes": {"columns": ["姓名", "部门"]},
                },
            ],
        }
    )

    candidates = FieldCandidateEngine().extract("task_test", uir)
    by_path = {candidate.source_path: candidate for candidate in candidates}

    assert by_path["metadata.文档标题"].value_sample == "SchemaPack 手册"
    assert by_path["blocks.heading_1.attributes.section_no"].value_sample == "1"
    assert by_path["blocks.heading_1.text"].source_name == "heading_title"
    assert by_path["blocks.paragraph_1.text.发布日期"].inferred_type == "date"
    assert by_path["blocks.table_1.table.姓名"].source_name == "姓名"
    assert by_path["blocks.table_1.table.部门"].source_name == "部门"
