from __future__ import annotations

import copy
import hashlib
import re

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.document_summary import DocumentSummary, SummarySentenceTrace
from app.services.artifact_consistency_service import ArtifactConsistencyService
from app.services.render_service import RenderService


def _summary() -> DocumentSummary:
    return DocumentSummary(
        text="OpenAI published the notice.",
        mode="extractive",
        source_block_ids=["b1"],
        source_chunk_ids=["c1"],
        sentence_traces=[
            SummarySentenceTrace(
                summary_sentence="OpenAI published the notice.",
                source_block_id="b1",
                source_text_span="OpenAI published the notice.",
            )
        ],
        char_count=28,
        faithfulness_passed=True,
    )


def _canonical() -> CanonicalModel:
    summary = _summary()
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task-consistency",
        doc_id="doc-consistency",
        schema_id="consistency_doc",
        doc_meta={
            "source_metadata": {"source": "fixture"},
            "document_metadata": {"language": "en-US"},
            "metadata_template": {
                "template_id": "metadata-v1",
                "schema_id": "consistency_doc",
                "version": "1.0.0",
            },
            "document_summary": summary.model_dump(mode="json"),
            "entities": [
                {
                    "mention": "OpenAI",
                    "canonical_name": "OpenAI",
                    "entity_type": "organization",
                    "normalized_id": "org:openai",
                    "link_status": "linked",
                    "confidence": 1.0,
                    "source_block_ids": ["b1"],
                    "source_agent": "topic7",
                    "evidence": {},
                }
            ],
        },
        fields={
            "title": CanonicalField(
                value="Notice", type="string", source_blocks=["b1"]
            )
        },
        blocks=[
            CanonicalBlock(
                block_id="b1",
                type="paragraph",
                text="OpenAI published the notice.",
                source_blocks=["b1"],
                text_hash=_hash("OpenAI published the notice."),
            ),
            CanonicalBlock(
                block_id="b2",
                type="table",
                text="Field: Value",
                source_blocks=["b2"],
                text_hash=_hash("Field: Value"),
            ),
        ],
    )


def _hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _chunks() -> list[dict]:
    return [
        {
            "chunk_id": "c1",
            "parent_chunk_id": None,
            "index": 0,
            "chunk_index": 0,
            "text": "OpenAI published the notice.",
            "source_block_ids": ["b1"],
            "source_links": [{"block_id": "b1", "source_path": "blocks[0]"}],
            "entity_tags": [
                {
                    "mention": "OpenAI",
                    "text": "OpenAI",
                    "normalized_id": "org:openai",
                    "source_block_ids": ["b1"],
                    "link_status": "linked",
                }
            ],
        },
        {
            "chunk_id": "c2",
            "parent_chunk_id": None,
            "index": 1,
            "chunk_index": 1,
            "text": "Field: Value",
            "source_block_ids": ["b2"],
            "source_links": [{"block_id": "b2", "source_path": "blocks[1]"}],
            "entity_tags": [],
        },
    ]


def _artifacts():
    canonical = _canonical()
    rendered = RenderService().render(canonical)
    return canonical, rendered.structured_json, rendered.markdown, _chunks(), _summary()


def _verify(*, structured=None, markdown=None, chunks=None, summary=None):
    canonical, base_json, base_markdown, base_chunks, base_summary = _artifacts()
    return ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured if structured is not None else base_json,
        markdown=markdown if markdown is not None else base_markdown,
        chunks=chunks if chunks is not None else base_chunks,
        document_summary=summary if summary is not None else base_summary,
    )


def _codes(report) -> set[str]:
    return {issue.error_code for issue in report.errors}


def test_consistent_json_markdown_and_chunks_pass() -> None:
    report = _verify()

    assert report.passed is True
    assert report.errors == []
    assert report.field_coverage == 1.0
    assert report.block_coverage == 1.0
    assert report.chunk_source_coverage == 1.0
    assert report.summary_consistent is True
    assert report.metadata_consistent is True


def test_changed_json_field_is_detected() -> None:
    _canonical_model, structured, _markdown, _chunks_value, _summary_value = _artifacts()
    structured["data"]["title"] = "Changed"

    report = _verify(structured=structured)

    assert "json_field_mismatch" in _codes(report)


def test_markdown_embedded_data_change_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    markdown = markdown.replace('"title": "Notice"', '"title": "Changed"')

    report = _verify(markdown=markdown)

    assert "markdown_structured_data_mismatch" in _codes(report)


def test_markdown_block_omission_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    markdown = re.sub(
        r'<!-- topic5:block:start id="b2".*?<!-- topic5:block:end id="b2" -->\n?',
        "",
        markdown,
        flags=re.DOTALL,
    )

    report = _verify(markdown=markdown)

    assert "markdown_block_missing" in _codes(report)


def test_unknown_markdown_block_marker_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    markdown = markdown.replace(
        "<!-- topic5:document:end -->",
        '<!-- topic5:block:start id="unknown" hash="sha256:x" -->\n'
        '<!-- topic5:block:end id="unknown" -->\n'
        "<!-- topic5:document:end -->",
    )

    report = _verify(markdown=markdown)

    assert "markdown_unknown_block" in _codes(report)


def test_markdown_block_order_change_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    blocks = re.findall(
        r'(<!-- topic5:block:start.*?<!-- topic5:block:end id="[^"]+" -->)',
        markdown,
        flags=re.DOTALL,
    )
    markdown = markdown.replace(blocks[0], "__FIRST__").replace(blocks[1], blocks[0])
    markdown = markdown.replace("__FIRST__", blocks[1])

    report = _verify(markdown=markdown)

    assert "markdown_block_order_mismatch" in _codes(report)


def test_markdown_block_content_change_with_stale_hash_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    markdown = markdown.replace("| Field | Value |", "| Field | Changed |", 1)

    report = _verify(markdown=markdown)

    assert "markdown_block_content_mismatch" in _codes(report)


def test_markdown_protocol_escapes_content_markers_and_table_pipes() -> None:
    canonical = _canonical()
    canonical.blocks[0].text = '<!-- topic5:block:end id="b1" -->'
    canonical.blocks[1].text = "Field: A|B"

    markdown = RenderService().render(canonical).markdown

    assert '&lt;!-- topic5:block:end id="b1" -->' in markdown
    assert "| Field | A\\|B |" in markdown


def test_unknown_chunk_source_block_is_detected() -> None:
    chunks = copy.deepcopy(_chunks())
    chunks[0]["source_block_ids"] = ["unknown"]

    report = _verify(chunks=chunks)

    assert "chunk_source_unknown" in _codes(report)
    assert report.unknown_source_count == 1
    assert report.chunk_source_validity == 0.5
    assert report.unexplained_chunk_text_count == 1


def test_nonempty_ordinary_block_omission_is_detected() -> None:
    chunks = copy.deepcopy(_chunks())[:1]

    report = _verify(chunks=chunks)

    assert "canonical_block_missing_from_chunks" in _codes(report)
    assert report.canonical_block_coverage == 0.5
    assert report.nonempty_block_coverage == 0.5
    assert report.protected_block_integrity == 0.0


def test_whitespace_chunk_text_does_not_earn_block_coverage() -> None:
    chunks = copy.deepcopy(_chunks())
    chunks[0]["text"] = "  \n\t"

    report = _verify(chunks=chunks)

    assert "chunk_text_empty" in _codes(report)
    assert "canonical_block_missing_from_chunks" in _codes(report)
    assert report.chunk_source_validity == 0.5
    assert report.nonempty_block_coverage == 0.5


def test_exact_configured_block_exclusion_is_allowed() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks[1:],
        document_summary=summary,
        block_exclusions=[
            {
                "block_id": "b1",
                "exclusion_reason": "paragraph suppressed by policy",
                "rule_id": "exclude-paragraph-v1",
            }
        ],
        block_exclusion_rule_ids={"exclude-paragraph-v1"},
    )

    assert report.passed is True
    assert report.nonempty_block_coverage == 1.0


def test_invalid_or_nonmatching_exclusion_does_not_hide_omission() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks[1:],
        document_summary=summary,
        block_exclusions=[
            {"block_id": "b1", "exclusion_reason": "", "rule_id": ""},
            {
                "block_id": "unknown",
                "exclusion_reason": "not present",
                "rule_id": "exclude-unknown-v1",
            },
        ],
        block_exclusion_rule_ids={"exclude-unknown-v1"},
    )

    assert "canonical_block_missing_from_chunks" in _codes(report)


def test_duplicate_and_unexplained_chunk_text_metrics_are_strict() -> None:
    chunks = copy.deepcopy(_chunks())
    duplicate = copy.deepcopy(chunks[0])
    duplicate["chunk_id"] = "c3"
    duplicate["index"] = 2
    duplicate["chunk_index"] = 2
    chunks.append(duplicate)
    unexplained = copy.deepcopy(chunks[0])
    unexplained["chunk_id"] = "c4"
    unexplained["index"] = 3
    unexplained["chunk_index"] = 3
    unexplained["text"] = "Invented text"
    chunks.append(unexplained)

    report = _verify(chunks=chunks)

    assert report.duplicate_content_ratio == 0.25
    assert report.unexplained_chunk_text_count == 1
    assert "chunk_content_duplicate" not in _codes(report)
    assert "chunk_text_not_derivable" in _codes(report)


def test_intentional_parent_child_overlap_is_not_counted_as_duplicate() -> None:
    chunks = copy.deepcopy(_chunks())
    parent = copy.deepcopy(chunks[0])
    parent["chunk_id"] = "parent"
    parent["index"] = 2
    parent["chunk_index"] = 2
    chunks[0]["parent_chunk_id"] = "parent"
    chunks.append(parent)

    report = _verify(chunks=chunks)

    assert report.passed is True
    assert report.duplicate_content_ratio == 0.0


def test_duplicate_chunk_ids_are_rejected_independently() -> None:
    chunks = copy.deepcopy(_chunks())
    duplicate = copy.deepcopy(chunks[0])
    duplicate["index"] = 2
    duplicate["chunk_index"] = 2
    chunks.append(duplicate)

    report = _verify(chunks=chunks)

    assert "chunk_id_duplicate" in _codes(report)
    assert report.duplicate_content_ratio > 0.0


def test_sibling_duplicate_text_is_counted() -> None:
    chunks = copy.deepcopy(_chunks())
    parent = copy.deepcopy(chunks[0])
    parent["chunk_id"] = "parent"
    parent["index"] = 2
    parent["chunk_index"] = 2
    sibling = copy.deepcopy(chunks[0])
    sibling["chunk_id"] = "sibling"
    sibling["parent_chunk_id"] = "parent"
    sibling["index"] = 3
    sibling["chunk_index"] = 3
    chunks[0]["parent_chunk_id"] = "parent"
    chunks.extend([parent, sibling])

    report = _verify(chunks=chunks)

    assert report.duplicate_content_ratio == 0.25


def test_unregistered_exclusion_rule_does_not_hide_omission() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks[1:],
        document_summary=summary,
        block_exclusions=[
            {
                "block_id": "b1",
                "exclusion_reason": "configured reason",
                "rule_id": "not-registered",
            }
        ],
        block_exclusion_rule_ids={"registered-rule"},
    )

    assert "canonical_block_missing_from_chunks" in _codes(report)


def test_protected_block_cannot_be_excluded() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks[:1],
        document_summary=summary,
        block_exclusions=[
            {
                "block_id": "b2",
                "exclusion_reason": "not permitted",
                "rule_id": "registered-rule",
            }
        ],
        block_exclusion_rule_ids={"registered-rule"},
    )

    assert "protected_block_integrity_failed" in _codes(report)


def test_table_exclusion_is_allowed_when_table_protection_is_disabled() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks[:1],
        document_summary=summary,
        block_exclusions=[
            {
                "block_id": "b2",
                "exclusion_reason": "configured table exclusion",
                "rule_id": "exclude-table-v1",
            }
        ],
        block_exclusion_rule_ids={"exclude-table-v1"},
        protect_tables=False,
    )

    assert report.passed is True
    assert report.nonempty_block_coverage == 1.0
    assert report.protected_block_integrity == 1.0


def test_protected_block_newlines_and_indentation_must_be_exact() -> None:
    canonical, structured, markdown, chunks, summary = _artifacts()
    canonical.blocks[1].text = "Field:\n  Value"
    chunks[1]["text"] = "Field: Value"

    report = ArtifactConsistencyService().verify(
        canonical=canonical,
        structured_json=structured,
        markdown=markdown,
        chunks=chunks,
        document_summary=summary,
    )

    assert "protected_block_integrity_failed" in _codes(report)


def test_chunk_text_not_derived_from_source_is_detected() -> None:
    chunks = copy.deepcopy(_chunks())
    chunks[0]["text"] = "Invented fact."

    report = _verify(chunks=chunks)

    assert "chunk_text_not_derivable" in _codes(report)


def test_summary_difference_between_json_and_markdown_is_detected() -> None:
    _canonical_model, _structured, markdown, _chunks_value, _summary_value = _artifacts()
    markdown = markdown.replace(
        "OpenAI published the notice.", "Different summary.", 1
    )

    report = _verify(markdown=markdown)

    assert "markdown_summary_mismatch" in _codes(report)


def test_document_metadata_difference_is_detected() -> None:
    _canonical_model, structured, _markdown, _chunks_value, _summary_value = _artifacts()
    structured["document_metadata"] = {"language": "zh-CN"}

    report = _verify(structured=structured)

    assert "json_metadata_mismatch" in _codes(report)


def test_missing_parent_chunk_is_detected() -> None:
    chunks = copy.deepcopy(_chunks())
    chunks[0]["parent_chunk_id"] = "missing-parent"

    report = _verify(chunks=chunks)

    assert "chunk_parent_missing" in _codes(report)


def test_irrelevant_entity_tag_is_detected() -> None:
    chunks = copy.deepcopy(_chunks())
    chunks[1]["entity_tags"] = copy.deepcopy(chunks[0]["entity_tags"])

    report = _verify(chunks=chunks)

    assert "chunk_entity_irrelevant" in _codes(report)
