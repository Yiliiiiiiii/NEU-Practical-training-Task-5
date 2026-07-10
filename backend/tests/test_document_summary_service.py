from __future__ import annotations

from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.content_organization import SummaryConfig
from app.services.document_summary_service import DocumentSummaryService


def _canonical(blocks: list[CanonicalBlock]) -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task-summary",
        doc_id="doc-summary",
        schema_id="summary_doc",
        blocks=blocks,
    )


def _block(block_id: str, text: str, *, block_type: str = "paragraph", level=None):
    return CanonicalBlock(
        block_id=block_id,
        type=block_type,
        level=level,
        text=text,
        source_blocks=[block_id],
    )


def _chunks() -> list[dict]:
    return [
        {"chunk_id": "c1", "source_block_ids": ["p1"]},
        {"chunk_id": "c2", "source_block_ids": ["p2", "p3"]},
    ]


def test_multi_section_summary_selects_first_source_sentence_per_section() -> None:
    canonical = _canonical(
        [
            _block("h1", "Overview", block_type="heading", level=1),
            _block("p1", "First overview fact. Second overview fact."),
            _block("h2", "Details", block_type="heading", level=1),
            _block("p2", "First detail fact. Second detail fact."),
        ]
    )

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(document_max_sentences=5, document_max_chars=500),
    )

    assert summary is not None
    assert summary.text == "First overview fact.\nFirst detail fact."
    assert summary.source_block_ids == ["p1", "p2"]
    assert summary.source_chunk_ids == ["c1", "c2"]
    assert [trace.source_text_span for trace in summary.sentence_traces] == [
        "First overview fact.",
        "First detail fact.",
    ]


def test_no_heading_fallback_selects_sentences_in_source_order() -> None:
    canonical = _canonical(
        [
            _block("p1", "Sentence one. Sentence two."),
            _block("p2", "Sentence three."),
        ]
    )

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(document_max_sentences=3, document_max_chars=500),
    )

    assert summary is not None
    assert summary.text == "Sentence one.\nSentence two.\nSentence three."


def test_duplicate_sentences_are_removed_after_whitespace_normalization() -> None:
    canonical = _canonical(
        [
            _block("p1", "Same fact.   Same fact."),
            _block("p2", "Same fact."),
        ]
    )

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(document_max_sentences=5, document_max_chars=500),
    )

    assert summary is not None
    assert summary.text == "Same fact."
    assert len(summary.sentence_traces) == 1


def test_summary_respects_sentence_limit() -> None:
    canonical = _canonical([_block("p1", "One. Two. Three.")])

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(document_max_sentences=2, document_max_chars=500),
    )

    assert summary is not None
    assert summary.text == "One.\nTwo."


def test_summary_respects_character_limit_without_new_text() -> None:
    canonical = _canonical([_block("p1", "A source sentence that is long.")])

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(document_max_sentences=5, document_max_chars=12),
    )

    assert summary is not None
    assert summary.text == "A source sen"
    assert summary.char_count == 12
    assert summary.sentence_traces[0].source_text_span == "A source sen"
    assert "summary_sentence_truncated" in summary.warnings


def test_empty_document_returns_empty_summary_with_warning() -> None:
    summary = DocumentSummaryService().build(
        canonical=_canonical([]),
        chunks=[],
        config=SummaryConfig(),
    )

    assert summary is not None
    assert summary.text == ""
    assert summary.faithfulness_passed is True
    assert summary.warnings == ["empty_document"]


def test_table_only_document_uses_exact_table_line() -> None:
    canonical = _canonical(
        [_block("t1", "Date: 2026-07-10\nAmount: CNY 100", block_type="table")]
    )

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=[{"chunk_id": "ct", "source_block_ids": ["t1"]}],
        config=SummaryConfig(document_max_sentences=1, document_max_chars=500),
    )

    assert summary is not None
    assert summary.text == "Date: 2026-07-10"
    assert summary.source_block_ids == ["t1"]
    assert summary.source_chunk_ids == ["ct"]


def test_extractiveness_prevents_new_date_amount_or_organization() -> None:
    source = "OpenAI announced CNY 100 on 2026-07-10."
    canonical = _canonical([_block("p1", source)])

    summary = DocumentSummaryService().build(
        canonical=canonical,
        chunks=_chunks(),
        config=SummaryConfig(),
    )

    assert summary is not None
    assert summary.text in source
    assert "2026-07-10" in summary.text
    assert "CNY 100" in summary.text
    assert "OpenAI" in summary.text
    assert summary.faithfulness_passed is True


def test_summary_disabled_returns_none() -> None:
    summary = DocumentSummaryService().build(
        canonical=_canonical([_block("p1", "Source fact.")]),
        chunks=_chunks(),
        config=SummaryConfig(document_mode="none"),
    )

    assert summary is None


def test_summary_repeated_runs_are_deterministic() -> None:
    canonical = _canonical([_block("p1", "First. Second.")])
    service = DocumentSummaryService()

    first = service.build(canonical=canonical, chunks=_chunks(), config=SummaryConfig())
    second = service.build(canonical=canonical, chunks=_chunks(), config=SummaryConfig())

    assert first == second
