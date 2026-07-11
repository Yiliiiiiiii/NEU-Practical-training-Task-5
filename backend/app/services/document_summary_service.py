from __future__ import annotations

import re
from typing import Any

from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.content_organization import SummaryConfig
from app.schemas.document_summary import DocumentSummary, SummarySentenceTrace


class DocumentSummaryService:
    def build(
        self,
        *,
        canonical: CanonicalModel,
        chunks: list[dict[str, Any]],
        config: SummaryConfig,
    ) -> DocumentSummary | None:
        if config.document_mode == "none":
            return None

        candidates = self._candidates(canonical.blocks)
        if not candidates:
            return DocumentSummary(
                text="",
                mode=config.document_mode,
                char_count=0,
                faithfulness_passed=True,
                warnings=["empty_document"],
            )

        selected: list[tuple[str, CanonicalBlock]] = []
        seen: set[str] = set()
        warnings: list[str] = []
        for sentence, block in candidates:
            normalized = self._normalize_spaces(sentence)
            if not normalized or normalized in seen:
                continue
            if len(selected) >= config.document_max_sentences:
                break
            current_length = sum(len(item[0]) for item in selected) + len(selected)
            remaining = config.document_max_chars - current_length
            if remaining <= 0:
                break
            if len(normalized) > remaining:
                if selected:
                    break
                normalized = normalized[:remaining].rstrip()
                if not normalized:
                    break
                warnings.append("summary_sentence_truncated")
            selected.append((normalized, block))
            seen.add(normalized)

        text = "\n".join(sentence for sentence, _block in selected)
        source_block_ids = self._dedupe(
            block.block_id for _sentence, block in selected
        )
        source_block_set = set(source_block_ids)
        source_chunk_ids = self._dedupe(
            str(chunk.get("chunk_id"))
            for chunk in chunks
            if chunk.get("chunk_id")
            and source_block_set.intersection(
                str(block_id) for block_id in chunk.get("source_block_ids", [])
            )
        )
        traces = [
            SummarySentenceTrace(
                summary_sentence=sentence,
                source_block_id=block.block_id,
                source_text_span=sentence,
            )
            for sentence, block in selected
        ]
        faithfulness_passed = all(
            trace.source_text_span in self._normalize_spaces(block.text)
            for trace, (_sentence, block) in zip(traces, selected, strict=True)
        )
        if not faithfulness_passed:
            warnings.append("summary_source_mismatch")
        return DocumentSummary(
            text=text,
            mode=config.document_mode,
            source_block_ids=source_block_ids,
            source_chunk_ids=source_chunk_ids,
            sentence_traces=traces,
            char_count=len(text),
            faithfulness_passed=faithfulness_passed,
            warnings=warnings,
        )

    def _candidates(
        self, blocks: list[CanonicalBlock]
    ) -> list[tuple[str, CanonicalBlock]]:
        has_headings = any(block.type == "heading" for block in blocks)
        if not has_headings:
            return [
                (sentence, block)
                for block in blocks
                if block.type != "heading"
                for sentence in self._sentences(block.text)
            ]

        candidates: list[tuple[str, CanonicalBlock]] = []
        section_selected = False
        for block in blocks:
            if block.type == "heading":
                section_selected = False
                continue
            sentences = self._sentences(block.text)
            if section_selected or not sentences:
                continue
            candidates.append((sentences[0], block))
            section_selected = True
        return candidates

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        sentences: list[str] = []
        for line in text.splitlines() or [text]:
            normalized = cls._normalize_spaces(line)
            if not normalized:
                continue
            sentences.extend(
                sentence
                for sentence in re.split(r"(?<=[。！？.!?])\s*", normalized)
                if sentence
            )
        return sentences

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _dedupe(values) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                output.append(value)
        return output
