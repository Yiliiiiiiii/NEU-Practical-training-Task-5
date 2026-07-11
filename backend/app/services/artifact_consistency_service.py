from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.schemas.artifact_consistency import (
    ArtifactConsistencyCheck,
    ArtifactConsistencyIssue,
    ArtifactConsistencyReport,
)
from app.schemas.canonical import CanonicalModel
from app.schemas.document_summary import DocumentSummary
from app.services.render_service import RenderService


class ArtifactConsistencyService:
    STRUCTURED_PATTERN = re.compile(
        r"<!-- topic5:structured-data:start -->\s*```json\s*(.*?)\s*```\s*"
        r"<!-- topic5:structured-data:end -->",
        re.DOTALL,
    )
    SUMMARY_PATTERN = re.compile(
        r"<!-- topic5:summary:start -->\n?(.*?)\n?<!-- topic5:summary:end -->",
        re.DOTALL,
    )
    BLOCK_PATTERN = re.compile(
        r'<!-- topic5:block:start id="([^"]+)" hash="([^"]+)" -->'
        r'(.*?)<!-- topic5:block:end id="([^"]+)" -->',
        re.DOTALL,
    )

    def verify(
        self,
        *,
        canonical: CanonicalModel,
        structured_json: dict[str, Any],
        markdown: str,
        chunks: list[dict[str, Any]],
        document_summary: DocumentSummary | None,
    ) -> ArtifactConsistencyReport:
        errors: list[ArtifactConsistencyIssue] = []
        checks: list[ArtifactConsistencyCheck] = []

        field_matches = self._check_fields(canonical, structured_json, errors)
        metadata_consistent = self._check_metadata(canonical, structured_json, errors)
        markdown_data_consistent = self._check_markdown_data(
            structured_json, markdown, errors
        )
        block_matches = self._check_markdown_blocks(canonical, markdown, errors)
        summary_consistent = self._check_summary(
            structured_json, markdown, document_summary, errors
        )
        sourced_chunks = self._check_chunks(canonical, chunks, errors)

        checks.extend(
            [
                self._check("fields", field_matches == len(canonical.fields)),
                self._check("metadata", metadata_consistent),
                self._check("markdown_structured_data", markdown_data_consistent),
                self._check("markdown_blocks", block_matches == len(canonical.blocks)),
                self._check("document_summary", summary_consistent),
                self._check("chunk_sources", sourced_chunks == len(chunks)),
            ]
        )
        return ArtifactConsistencyReport(
            passed=not errors,
            checks=checks,
            errors=errors,
            warnings=[],
            field_coverage=self._coverage(field_matches, len(canonical.fields)),
            block_coverage=self._coverage(block_matches, len(canonical.blocks)),
            chunk_source_coverage=self._coverage(sourced_chunks, len(chunks)),
            summary_consistent=summary_consistent,
            metadata_consistent=metadata_consistent,
        )

    def _check_fields(
        self,
        canonical: CanonicalModel,
        structured: dict[str, Any],
        errors: list[ArtifactConsistencyIssue],
    ) -> int:
        actual = structured.get("data")
        if not isinstance(actual, dict):
            self._error(errors, "data", "json_fields_invalid", "data must be an object.")
            return 0
        matches = 0
        expected = {key: value.value for key, value in canonical.fields.items()}
        for field_id, value in expected.items():
            if field_id in actual and actual[field_id] == value:
                matches += 1
            else:
                self._error(
                    errors,
                    f"data.{field_id}",
                    "json_field_mismatch",
                    "Structured field does not match the canonical value.",
                )
        for field_id in actual.keys() - expected.keys():
            self._error(
                errors,
                f"data.{field_id}",
                "json_field_unknown",
                "Structured output contains a field absent from canonical data.",
            )
        return matches

    def _check_metadata(
        self,
        canonical: CanonicalModel,
        structured: dict[str, Any],
        errors: list[ArtifactConsistencyIssue],
    ) -> bool:
        expected = canonical.doc_meta.get("document_metadata", {})
        actual = structured.get("document_metadata")
        if actual == expected:
            return True
        self._error(
            errors,
            "document_metadata",
            "json_metadata_mismatch",
            "Document metadata does not match canonical metadata.",
        )
        return False

    def _check_markdown_data(
        self,
        structured: dict[str, Any],
        markdown: str,
        errors: list[ArtifactConsistencyIssue],
    ) -> bool:
        match = self.STRUCTURED_PATTERN.search(markdown)
        if not match:
            self._error(
                errors,
                "content.md.structured_data",
                "markdown_structured_data_missing",
                "Markdown structured-data envelope is missing.",
            )
            return False
        try:
            embedded = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            self._error(
                errors,
                "content.md.structured_data",
                "markdown_structured_data_invalid",
                str(exc),
            )
            return False
        expected = {
            "data": structured.get("data", {}),
            "document_metadata": structured.get("document_metadata", {}),
        }
        if embedded == expected:
            return True
        self._error(
            errors,
            "content.md.structured_data",
            "markdown_structured_data_mismatch",
            "Markdown embedded data does not match structured JSON.",
        )
        return False

    def _check_markdown_blocks(
        self,
        canonical: CanonicalModel,
        markdown: str,
        errors: list[ArtifactConsistencyIssue],
    ) -> int:
        expected_ids = [block.block_id for block in canonical.blocks]
        expected_by_id = {block.block_id: block for block in canonical.blocks}
        matches = list(self.BLOCK_PATTERN.finditer(markdown))
        actual_ids = [match.group(1) for match in matches]
        matched_ids = 0

        for block_id in expected_ids:
            count = actual_ids.count(block_id)
            if count == 0:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}",
                    "markdown_block_missing",
                    "Canonical block is missing from Markdown.",
                )
            elif count > 1:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}",
                    "markdown_block_duplicate",
                    "Canonical block appears more than once in Markdown.",
                )
            else:
                matched_ids += 1

        for match in matches:
            block_id, marker_hash, content, end_id = match.groups()
            if block_id not in expected_by_id:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}",
                    "markdown_unknown_block",
                    "Markdown contains an unknown block marker.",
                )
                continue
            if end_id != block_id:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}",
                    "markdown_block_boundary_mismatch",
                    "Markdown block start and end identifiers differ.",
                )
            expected_hash = self._hash(expected_by_id[block_id].text)
            if marker_hash != expected_hash:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}.hash",
                    "markdown_block_hash_mismatch",
                    "Markdown block hash does not match canonical text.",
                )
            expected_content = "\n".join(
                RenderService.markdown_block_content(expected_by_id[block_id])
            )
            if content.strip("\n") != expected_content:
                self._error(
                    errors,
                    f"content.md.blocks.{block_id}.content",
                    "markdown_block_content_mismatch",
                    "Markdown block content does not match canonical rendering.",
                )
        known_actual_ids = [item for item in actual_ids if item in expected_by_id]
        if known_actual_ids != expected_ids:
            self._error(
                errors,
                "content.md.blocks",
                "markdown_block_order_mismatch",
                "Markdown block order does not match canonical order.",
            )
        return matched_ids

    def _check_summary(
        self,
        structured: dict[str, Any],
        markdown: str,
        document_summary: DocumentSummary | None,
        errors: list[ArtifactConsistencyIssue],
    ) -> bool:
        expected_payload = (
            document_summary.model_dump(mode="json") if document_summary else {}
        )
        json_payload = structured.get("document_summary")
        json_matches = json_payload == expected_payload
        if not json_matches:
            self._error(
                errors,
                "document_summary",
                "json_summary_mismatch",
                "Structured summary does not match the summary artifact.",
            )
        match = self.SUMMARY_PATTERN.search(markdown)
        markdown_text = match.group(1).strip() if match else None
        expected_text = document_summary.text if document_summary else ""
        markdown_matches = markdown_text == expected_text
        if not markdown_matches:
            self._error(
                errors,
                "content.md.document_summary",
                "markdown_summary_mismatch",
                "Markdown summary does not match the summary artifact.",
            )
        return json_matches and markdown_matches

    def _check_chunks(
        self,
        canonical: CanonicalModel,
        chunks: list[dict[str, Any]],
        errors: list[ArtifactConsistencyIssue],
    ) -> int:
        blocks = {block.block_id: block for block in canonical.blocks}
        chunk_ids = {
            str(chunk.get("chunk_id"))
            for chunk in chunks
            if chunk.get("chunk_id")
        }
        sourced = 0
        seen_indices: set[int] = set()
        entities = canonical.doc_meta.get("entities", [])
        entities = entities if isinstance(entities, list) else []

        for position, chunk in enumerate(chunks):
            path = f"chunks[{position}]"
            source_ids = [str(value) for value in chunk.get("source_block_ids", [])]
            known_ids = [value for value in source_ids if value in blocks]
            unknown_ids = [value for value in source_ids if value not in blocks]
            if unknown_ids or not source_ids:
                self._error(
                    errors,
                    f"{path}.source_block_ids",
                    "chunk_source_unknown",
                    "Chunk source identifiers must reference canonical blocks.",
                )
            else:
                sourced += 1

            links = chunk.get("source_links", [])
            if isinstance(links, list):
                for link_index, link in enumerate(links):
                    if not isinstance(link, dict) or link.get("block_id") not in source_ids:
                        self._error(
                            errors,
                            f"{path}.source_links[{link_index}]",
                            "chunk_source_link_mismatch",
                            "Chunk source link is not declared by source_block_ids.",
                        )

            source_text = "\n".join(blocks[item].text for item in known_ids)
            chunk_text = str(chunk.get("text") or "")
            if known_ids and not self._derivable(chunk_text, source_text):
                self._error(
                    errors,
                    f"{path}.text",
                    "chunk_text_not_derivable",
                    "Chunk text is not derivable from its declared source blocks.",
                )

            parent_id = chunk.get("parent_chunk_id")
            if parent_id and str(parent_id) not in chunk_ids:
                self._error(
                    errors,
                    f"{path}.parent_chunk_id",
                    "chunk_parent_missing",
                    "Chunk parent does not exist in the chunk set.",
                )

            index = chunk.get("index", chunk.get("chunk_index"))
            if not isinstance(index, int) or index in seen_indices:
                self._error(
                    errors,
                    f"{path}.index",
                    "chunk_index_invalid",
                    "Chunk indices must be unique integers.",
                )
            else:
                seen_indices.add(index)

            self._check_entity_tags(
                entity_tags=chunk.get("entity_tags", []),
                entities=entities,
                source_ids=set(source_ids),
                chunk_text=chunk_text,
                path=path,
                errors=errors,
            )
        return sourced

    def _check_entity_tags(
        self,
        *,
        entity_tags: object,
        entities: list[object],
        source_ids: set[str],
        chunk_text: str,
        path: str,
        errors: list[ArtifactConsistencyIssue],
    ) -> None:
        if not isinstance(entity_tags, list):
            return
        for index, tag in enumerate(entity_tags):
            if not isinstance(tag, dict):
                relevant = False
            else:
                relevant = any(
                    self._entity_relevant(tag, entity, source_ids, chunk_text)
                    for entity in entities
                    if isinstance(entity, dict)
                )
            if not relevant:
                self._error(
                    errors,
                    f"{path}.entity_tags[{index}]",
                    "chunk_entity_irrelevant",
                    "Chunk entity tag lacks matching source evidence.",
                )

    @staticmethod
    def _entity_relevant(
        tag: dict[str, Any],
        entity: dict[str, Any],
        source_ids: set[str],
        chunk_text: str,
    ) -> bool:
        tag_identity = tag.get("normalized_id") or tag.get("mention") or tag.get("text")
        entity_identity = entity.get("normalized_id") or entity.get("mention")
        if not tag_identity or tag_identity != entity_identity:
            return False
        entity_sources = {
            str(value) for value in entity.get("source_block_ids", []) if value
        }
        if entity_sources:
            return bool(entity_sources & source_ids)
        mention = str(entity.get("mention") or tag.get("mention") or "")
        return bool(mention and mention in chunk_text)

    @staticmethod
    def _derivable(chunk_text: str, source_text: str) -> bool:
        normalized_chunk = " ".join(chunk_text.split())
        normalized_source = " ".join(source_text.split())
        return not normalized_chunk or normalized_chunk in normalized_source

    @staticmethod
    def _hash(text: str) -> str:
        return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _coverage(matches: int, total: int) -> float:
        return 1.0 if total == 0 else matches / total

    @staticmethod
    def _check(name: str, passed: bool) -> ArtifactConsistencyCheck:
        return ArtifactConsistencyCheck(check_name=name, passed=passed)

    @staticmethod
    def _error(
        errors: list[ArtifactConsistencyIssue],
        path: str,
        code: str,
        message: str,
    ) -> None:
        errors.append(
            ArtifactConsistencyIssue(path=path, error_code=code, message=message)
        )
