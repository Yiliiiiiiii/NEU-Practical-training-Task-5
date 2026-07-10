import re
from collections import Counter
from typing import Any

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.content_organization import (
    ChunkTags,
    ContentOrganizationOptions,
    ContentOrganizationReport,
    EntityTag,
    OrganizedChunk,
    SourceLink,
)
from app.schemas.reports import MappingReport, ValidationReport
from app.schemas.target_schema import TargetField, TargetSchema
from app.services.tag_rule_service import TagRuleService


class ChunkOrganizerService:
    STOPWORDS = {
        "的",
        "了",
        "和",
        "与",
        "及",
        "或",
        "在",
        "对",
        "为",
        "是",
        "本",
        "该",
        "等",
        "this",
        "that",
        "and",
        "or",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "for",
    }
    ENTITY_HINTS = (
        "entity",
        "company",
        "organization",
        "organizer",
        "issuer",
        "person",
        "party",
        "department",
        "机构",
        "部门",
        "人员",
        "甲方",
        "乙方",
    )

    def organize_chunks(
        self,
        *,
        chunks: list[dict[str, Any]],
        canonical_model: CanonicalModel,
        schema: TargetSchema,
        mapping_report: MappingReport,
        validation_report: ValidationReport | None,
        task_id: str,
        doc_id: str,
        schema_id: str,
        template_id: str,
        template_version: str | None = None,
        options: ContentOrganizationOptions | dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], ContentOrganizationReport]:
        warnings: list[str] = []
        organization_options = self._normalize_options(options)
        tag_options = organization_options or ContentOrganizationOptions()
        raw_chunks = chunks
        if organization_options is not None:
            raw_chunks = self._build_strategy_chunks(
                canonical_model=canonical_model,
                doc_id=doc_id,
                task_id=task_id,
                options=organization_options,
            )

        if not raw_chunks:
            warnings.append("no_chunks_to_organize")

        blocks_by_id = {block.block_id: block for block in canonical_model.blocks}
        block_positions = {
            block.block_id: index
            for index, block in enumerate(canonical_model.blocks)
        }
        fields_by_id = {field.field_id: field for field in schema.fields}
        entity_candidates = self._entity_candidates(
            canonical_model=canonical_model,
            fields_by_id=fields_by_id,
        )

        organized: list[dict[str, Any]] = []
        tag_service = TagRuleService()
        for index, chunk in enumerate(raw_chunks):
            text = str(chunk.get("text") or "")
            token_estimate = self.estimate_tokens(text)
            source_block_ids = [
                str(block_id)
                for block_id in chunk.get("source_block_ids", [])
                if block_id
            ]
            source_links = self._source_links(
                source_block_ids=source_block_ids,
                blocks_by_id=blocks_by_id,
                block_positions=block_positions,
            )
            summary = self.summarize_text(text)
            keywords = self.extract_keywords(
                text,
                schema=schema,
                metadata=canonical_model.doc_meta.get("metadata", {}),
                title_path=chunk.get("title_path", []),
            ) if organization_options is None or organization_options.keyword_mode != "none" else []
            if organization_options is not None and organization_options.summary_mode == "none":
                summary = ""
            quality_flags = sorted(
                {
                    str(flag)
                    for flag in chunk.get("quality_flags", [])
                    if flag
                }
            )
            chunk_id = str(chunk.get("chunk_id") or f"chunk_{doc_id}_{index:04d}")
            title_path = list(chunk.get("title_path", []))
            entity_tags = self._chunk_entity_tags(
                text=text,
                source_block_ids=source_block_ids,
                entity_candidates=entity_candidates,
            )
            block_types = sorted(
                {
                    blocks_by_id[block_id].type
                    for block_id in source_block_ids
                    if block_id in blocks_by_id
                }
            )
            content_tags, content_tag_traces = tag_service.content_tags(
                text=text,
                title_path=title_path,
                block_types=block_types,
                source_block_ids=source_block_ids,
                schema_id=schema_id,
                options=tag_options,
            )
            management_tags, management_tag_traces = tag_service.management_tags(
                canonical=canonical_model,
                schema=schema,
                template_id=template_id,
                template_version=template_version,
                source_block_ids=source_block_ids,
                options=tag_options,
            )
            quality_tags, quality_tag_traces = tag_service.quality_tags(
                chunk_id=chunk_id,
                text=text,
                token_estimate=token_estimate,
                source_block_ids=source_block_ids,
                source_links=source_links,
                summary=summary,
                keywords=keywords,
                quality_flags=quality_flags,
                entity_tags=[tag.model_dump(mode="json") for tag in entity_tags],
                canonical=canonical_model,
                mapping_report=mapping_report,
                validation_report=validation_report,
                options=tag_options,
            )
            tags = ChunkTags(
                content=content_tags,
                management=management_tags,
                quality=quality_tags,
            )
            organized_chunk = OrganizedChunk(
                chunk_id=chunk_id,
                parent_chunk_id=chunk.get("parent_chunk_id"),
                doc_id=doc_id,
                task_id=task_id,
                index=index,
                chunk_index=int(chunk.get("chunk_index", index)),
                strategy=str(
                    chunk.get("strategy")
                    or (organization_options.chunk_strategy if organization_options else "legacy")
                ),
                granularity=chunk.get("granularity"),
                text=text,
                token_estimate=token_estimate,
                char_count=len(text),
                title=title_path[-1] if title_path else None,
                title_path=title_path,
                source_block_ids=source_block_ids,
                source_links=source_links,
                content_tags=tags.content,
                management_tags=tags.management,
                quality_tags=tags.quality,
                quality_flags=quality_flags,
                tags=tags,
                keywords=keywords,
                summary=summary,
                entity_tags=entity_tags,
                organization_trace={
                    "summary_strategy": "first_sentence_or_prefix",
                    "keyword_strategy": "frequency_with_stopwords",
                    "tag_strategy": "schema_and_rule_based",
                    "source_link_strategy": "canonical_block_anchor_or_path",
                    "tag_traces": [
                        *content_tag_traces,
                        *management_tag_traces,
                        *quality_tag_traces,
                    ],
                    **{
                        key: value
                        for key, value in chunk.get("organization_trace", {}).items()
                        if value is not None
                    },
                },
            )
            organized.append(organized_chunk.model_dump(mode="json"))

        document_quality_flags = tag_service.document_quality_flags(
            chunks=organized,
            canonical=canonical_model,
            mapping_report=mapping_report,
            validation_report=validation_report,
            options=tag_options,
        )
        report = self._report(
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            template_id=template_id,
            organized=organized,
            options=organization_options,
            warnings=warnings,
            document_quality_flags=document_quality_flags,
            tag_options=tag_options,
        )
        return organized, report

    @staticmethod
    def _normalize_options(
        options: ContentOrganizationOptions | dict[str, Any] | None,
    ) -> ContentOrganizationOptions | None:
        if options is None:
            return None
        if isinstance(options, ContentOrganizationOptions):
            return options
        return ContentOrganizationOptions.model_validate(options)

    def _build_strategy_chunks(
        self,
        *,
        canonical_model: CanonicalModel,
        doc_id: str,
        task_id: str,
        options: ContentOrganizationOptions,
    ) -> list[dict[str, Any]]:
        if options.chunk_strategy == "fixed_window":
            return self._fixed_window_chunks(
                canonical_model=canonical_model,
                doc_id=doc_id,
                task_id=task_id,
                options=options,
            )
        child_chunks = self._block_aware_chunks(
            canonical_model=canonical_model,
            doc_id=doc_id,
            task_id=task_id,
            options=options,
            granularity="child" if self._parent_child_enabled(options) else None,
        )
        if not self._parent_child_enabled(options):
            return child_chunks
        parent_chunks = self._parent_chunks(
            canonical_model=canonical_model,
            doc_id=doc_id,
            task_id=task_id,
            options=options,
        )
        parent_by_title = {
            tuple(chunk.get("title_path") or ["document"]): chunk["chunk_id"]
            for chunk in parent_chunks
        }
        fallback_parent = parent_chunks[0]["chunk_id"] if parent_chunks else None
        for chunk in child_chunks:
            title_path = chunk.get("title_path") or ["document"]
            parent_key = (title_path[0],) if title_path else ("document",)
            chunk["parent_chunk_id"] = parent_by_title.get(parent_key, fallback_parent)
        return parent_chunks + child_chunks

    @staticmethod
    def _parent_child_enabled(options: ContentOrganizationOptions) -> bool:
        return options.enable_parent_child or options.chunk_strategy == "parent_child"

    def _fixed_window_chunks(
        self,
        *,
        canonical_model: CanonicalModel,
        doc_id: str,
        task_id: str,
        options: ContentOrganizationOptions,
    ) -> list[dict[str, Any]]:
        text_parts: list[str] = []
        source_block_ids: list[str] = []
        for block in canonical_model.blocks:
            text = block.text.strip()
            if not text:
                continue
            text_parts.append(text)
            source_block_ids.extend(self._block_source_ids(block))
        text = "\n\n".join(text_parts)
        pieces = self.split_on_sentence_boundary(text, options.max_tokens)
        return [
            self._raw_chunk(
                chunk_id=f"chunk_{task_id}_{index:04d}",
                text=piece,
                source_block_ids=self._dedupe(source_block_ids),
                title_path=[],
                strategy=options.chunk_strategy,
                chunk_index=index,
                split_reason="fixed_window",
            )
            for index, piece in enumerate(pieces)
        ]

    def _block_aware_chunks(
        self,
        *,
        canonical_model: CanonicalModel,
        doc_id: str,
        task_id: str,
        options: ContentOrganizationOptions,
        granularity: str | None,
    ) -> list[dict[str, Any]]:
        if options.chunk_strategy == "source_block_aware":
            return self._source_block_chunks(
                canonical_model=canonical_model,
                task_id=task_id,
                options=options,
                granularity=granularity,
            )

        chunks: list[dict[str, Any]] = []
        current_units: list[dict[str, Any]] = []
        title_path: list[str] = []

        def flush(split_reason: str) -> None:
            if not current_units:
                return
            chunk = self._merge_units(
                current_units,
                task_id=task_id,
                chunk_index=len(chunks),
                strategy=options.chunk_strategy,
                split_reason=split_reason,
                granularity=granularity,
            )
            chunks.append(chunk)
            current_units.clear()

        for block in canonical_model.blocks:
            text = block.text.strip()
            if not text:
                continue
            if self.is_heading_block(block):
                flush("heading_boundary")
                title_path = title_path[: max((block.level or 1) - 1, 0)] + [text]
                if options.chunk_strategy == "heading_aware":
                    current_units.append(self._block_unit(block, title_path, options))
                continue

            unit = self._block_unit(block, title_path, options)
            protected = bool(unit["protected"])
            if protected:
                flush("protected_block_boundary")
                chunks.append(
                    self._unit_to_chunk(
                        unit,
                        task_id=task_id,
                        chunk_index=len(chunks),
                        strategy=options.chunk_strategy,
                        split_reason="protected_block",
                        granularity=granularity,
                    )
                )
                continue

            proposed_tokens = self._units_token_estimate([*current_units, unit])
            if current_units and proposed_tokens > options.max_tokens:
                flush("max_tokens")
            current_units.append(unit)
        flush("end_of_document")
        return chunks

    def _source_block_chunks(
        self,
        *,
        canonical_model: CanonicalModel,
        task_id: str,
        options: ContentOrganizationOptions,
        granularity: str | None,
    ) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        title_path: list[str] = []
        for block in canonical_model.blocks:
            text = block.text.strip()
            if not text:
                continue
            if self.is_heading_block(block):
                title_path = title_path[: max((block.level or 1) - 1, 0)] + [text]
            unit = self._block_unit(block, title_path, options)
            chunks.append(
                self._unit_to_chunk(
                    unit,
                    task_id=task_id,
                    chunk_index=len(chunks),
                    strategy=options.chunk_strategy,
                    split_reason="source_block_boundary",
                    granularity=granularity,
                )
            )
        return chunks

    def _parent_chunks(
        self,
        *,
        canonical_model: CanonicalModel,
        doc_id: str,
        task_id: str,
        options: ContentOrganizationOptions,
    ) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        title_path: list[str] = []
        for block in canonical_model.blocks:
            text = block.text.strip()
            if not text:
                continue
            if self.is_heading_block(block):
                title_path = title_path[: max((block.level or 1) - 1, 0)] + [text]
                if (block.level or 1) <= 1 or current is None:
                    current = {
                        "title_path": [title_path[0]],
                        "texts": [],
                        "source_block_ids": [],
                    }
                    sections.append(current)
            if current is None:
                current = {
                    "title_path": ["document"],
                    "texts": [],
                    "source_block_ids": [],
                }
                sections.append(current)
            current["texts"].append(text)
            current["source_block_ids"].extend(self._block_source_ids(block))

        parent_chunks: list[dict[str, Any]] = []
        for index, section in enumerate(sections):
            text = "\n\n".join(section["texts"])
            quality_flags = []
            if self.estimate_tokens(text) > options.max_tokens:
                quality_flags.append("oversized_chunk")
            parent_chunks.append(
                self._raw_chunk(
                    chunk_id=f"chunk_{task_id}_parent_{index:04d}",
                    text=text,
                    source_block_ids=self._dedupe(section["source_block_ids"]),
                    title_path=section["title_path"],
                    strategy=options.chunk_strategy,
                    chunk_index=index,
                    split_reason="parent_heading_group",
                    granularity="parent",
                    quality_flags=quality_flags,
                )
            )
        return parent_chunks

    def _block_unit(
        self,
        block: CanonicalBlock,
        title_path: list[str],
        options: ContentOrganizationOptions,
    ) -> dict[str, Any]:
        protected = self._is_protected_block(block, options)
        quality_flags = []
        if protected and self.estimate_tokens(block.text) > options.max_tokens:
            quality_flags.append("oversized_protected_block")
        return {
            "block_id": block.block_id,
            "text": block.text.strip(),
            "title_path": list(title_path),
            "source_block_ids": self._block_source_ids(block),
            "protected": protected,
            "quality_flags": quality_flags,
        }

    def _unit_to_chunk(
        self,
        unit: dict[str, Any],
        *,
        task_id: str,
        chunk_index: int,
        strategy: str,
        split_reason: str,
        granularity: str | None,
    ) -> dict[str, Any]:
        return self._raw_chunk(
            chunk_id=f"chunk_{task_id}_{chunk_index:04d}",
            text=str(unit["text"]),
            source_block_ids=list(unit["source_block_ids"]),
            title_path=list(unit["title_path"]),
            strategy=strategy,
            chunk_index=chunk_index,
            split_reason=split_reason,
            protected_blocks=[unit["block_id"]] if unit.get("protected") else [],
            granularity=granularity,
            quality_flags=list(unit.get("quality_flags", [])),
        )

    def _merge_units(
        self,
        units: list[dict[str, Any]],
        *,
        task_id: str,
        chunk_index: int,
        strategy: str,
        split_reason: str,
        granularity: str | None,
    ) -> dict[str, Any]:
        source_block_ids: list[str] = []
        quality_flags: list[str] = []
        for unit in units:
            source_block_ids.extend(unit["source_block_ids"])
            quality_flags.extend(unit.get("quality_flags", []))
        return self._raw_chunk(
            chunk_id=f"chunk_{task_id}_{chunk_index:04d}",
            text="\n\n".join(str(unit["text"]) for unit in units),
            source_block_ids=self._dedupe(source_block_ids),
            title_path=list(units[-1].get("title_path", [])),
            strategy=strategy,
            chunk_index=chunk_index,
            split_reason=split_reason,
            granularity=granularity,
            quality_flags=self._dedupe(quality_flags),
        )

    @staticmethod
    def _raw_chunk(
        *,
        chunk_id: str,
        text: str,
        source_block_ids: list[str],
        title_path: list[str],
        strategy: str,
        chunk_index: int,
        split_reason: str,
        protected_blocks: list[str] | None = None,
        granularity: str | None = None,
        quality_flags: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "chunk_id": chunk_id,
            "text": text,
            "source_block_ids": source_block_ids,
            "title_path": title_path,
            "strategy": strategy,
            "chunk_index": chunk_index,
            "granularity": granularity,
            "quality_flags": quality_flags or [],
            "organization_trace": {
                "split_reason": split_reason,
                "merge_reason": None,
                "protected_blocks": protected_blocks or [],
            },
        }

    @classmethod
    def _is_protected_block(
        cls,
        block: CanonicalBlock,
        options: ContentOrganizationOptions,
    ) -> bool:
        return (
            (options.protect_tables and cls.is_table_block(block))
            or (options.protect_lists and cls.is_list_block(block))
            or (options.protect_code_blocks and cls.is_code_block(block))
        )

    @staticmethod
    def is_heading_block(block: CanonicalBlock) -> bool:
        return block.type == "heading"

    @staticmethod
    def is_table_block(block: CanonicalBlock) -> bool:
        return block.type == "table"

    @staticmethod
    def is_list_block(block: CanonicalBlock) -> bool:
        return block.type == "list"

    @staticmethod
    def is_code_block(block: CanonicalBlock) -> bool:
        return block.type in {"code", "code_block"}

    @staticmethod
    def _block_source_ids(block: CanonicalBlock) -> list[str]:
        return list(block.source_blocks or [block.block_id])

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    def _units_token_estimate(self, units: list[dict[str, Any]]) -> int:
        return self.estimate_tokens("\n\n".join(str(unit["text"]) for unit in units))

    def split_on_sentence_boundary(self, text: str, max_tokens: int) -> list[str]:
        if self.estimate_tokens(text) <= max_tokens:
            return [text] if text else []
        max_chars = max(max_tokens * 4, 1)
        sentences = [
            sentence.strip()
            for sentence in re.findall(r"[^。！？!?\n.]+[。！？!?.]*", text)
            if sentence.strip()
        ]
        if not sentences:
            return [
                text[index : index + max_chars]
                for index in range(0, len(text), max_chars)
            ]
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            proposed = f"{current} {sentence}".strip() if current else sentence
            if current and self.estimate_tokens(proposed) > max_tokens:
                pieces.append(current)
                current = sentence
            else:
                current = proposed
        if current:
            pieces.append(current)
        return pieces

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        other_count = len(text) - cjk_count
        return max(1, int(cjk_count / 1.5 + other_count / 4))

    @classmethod
    def summarize_text(cls, text: str, max_chars: int = 120) -> str:
        cleaned = cls._normalize_spaces(text)
        if not cleaned:
            return ""
        sentences = [
            sentence.strip()
            for sentence in re.findall(r"[^。！？!?；;\n.]+[。！？!?；;.]*", cleaned)
            if sentence.strip()
        ]
        if sentences:
            summary = sentences[0]
            if len(summary) < 20 and len(sentences) > 1:
                summary = f"{summary}{sentences[1]}"
            if len(summary) <= max_chars:
                return summary
        suffix = "..." if len(cleaned) > max_chars else ""
        return cleaned[:max_chars].rstrip() + suffix

    @classmethod
    def extract_keywords(
        cls,
        text: str,
        *,
        schema: TargetSchema,
        metadata: dict[str, Any],
        title_path: list[str],
        limit: int = 8,
    ) -> list[str]:
        candidates = cls._keyword_candidates(text)
        counts = Counter(token for token in candidates if token.lower() not in cls.STOPWORDS)
        priority_text = " ".join(
            [
                *title_path,
                *[str(value) for value in metadata.values() if isinstance(value, str)],
                *[
                    value
                    for field in schema.fields
                    for value in (field.field_id, field.name, field.display_name, *field.aliases)
                    if value
                ],
            ]
        )
        priority_terms = set(cls._keyword_candidates(priority_text))
        for term in priority_terms:
            if term in counts:
                counts[term] += 2
        return [
            token
            for token, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            [:limit]
        ]

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _keyword_candidates(text: str) -> list[str]:
        return re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}", text)

    @classmethod
    def _source_links(
        cls,
        *,
        source_block_ids: list[str],
        blocks_by_id: dict[str, CanonicalBlock],
        block_positions: dict[str, int],
    ) -> list[SourceLink]:
        links: list[SourceLink] = []
        for block_id in source_block_ids:
            block = blocks_by_id.get(block_id)
            anchor = block.source_anchor if block else None
            links.append(
                SourceLink(
                    block_id=block_id,
                    source_path=f"blocks[{block_positions[block_id]}]"
                    if block_id in block_positions
                    else None,
                    page_no=anchor.get("page") if isinstance(anchor, dict) else None,
                    bbox=anchor.get("bbox") if isinstance(anchor, dict) else None,
                    anchor_text=cls._normalize_spaces(block.text)[:20] if block else None,
                )
            )
        return links

    @classmethod
    def _entity_candidates(
        cls,
        *,
        canonical_model: CanonicalModel,
        fields_by_id: dict[str, TargetField],
    ) -> list[tuple[EntityTag, list[str]]]:
        candidates: list[tuple[EntityTag, list[str]]] = []
        for field_id, field_value in canonical_model.fields.items():
            target_field = fields_by_id.get(field_id)
            field_label = " ".join(
                value
                for value in (
                    field_id,
                    target_field.name if target_field else "",
                    target_field.display_name if target_field else "",
                )
                if value
            )
            if not cls._is_entity_like(field_label):
                continue
            for text in cls._field_text_values(field_value):
                candidates.append(
                    (
                        EntityTag(
                            text=text,
                            entity_type=cls._entity_type_for_field(field_label),
                            normalized_id=None,
                            source="schema_field",
                            confidence=0.8,
                        ),
                        field_value.source_blocks,
                    )
                )

        metadata = canonical_model.doc_meta.get("metadata", {})
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if not cls._is_entity_like(str(key)):
                    continue
                for text in cls._raw_text_values(value):
                    candidates.append(
                        (
                            EntityTag(
                                text=text,
                                entity_type=cls._entity_type_for_field(str(key)),
                                normalized_id=None,
                                source="metadata",
                                confidence=0.7,
                            ),
                            [],
                        )
                    )
        return candidates

    @classmethod
    def _chunk_entity_tags(
        cls,
        *,
        text: str,
        source_block_ids: list[str],
        entity_candidates: list[tuple[EntityTag, list[str]]],
    ) -> list[EntityTag]:
        tags: dict[tuple[str, str], EntityTag] = {}
        source_block_set = set(source_block_ids)
        for tag, entity_source_blocks in entity_candidates:
            source_matches = bool(source_block_set.intersection(entity_source_blocks))
            text_matches = tag.text and tag.text in text
            if source_matches or text_matches:
                tags[(tag.text, tag.entity_type)] = tag
        return [tags[key] for key in sorted(tags)]

    @classmethod
    def _is_entity_like(cls, value: str) -> bool:
        normalized = value.lower()
        return any(hint in normalized for hint in cls.ENTITY_HINTS)

    @staticmethod
    def _field_text_values(field_value: CanonicalField) -> list[str]:
        return ChunkOrganizerService._raw_text_values(field_value.value)

    @staticmethod
    def _raw_text_values(value: Any) -> list[str]:
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            return [
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            ]
        return []

    @staticmethod
    def _entity_type_for_field(value: str) -> str:
        normalized = value.lower()
        if "person" in normalized or "人员" in normalized:
            return "person"
        if "party" in normalized or "甲方" in normalized or "乙方" in normalized:
            return "party"
        if any(
            hint in normalized
            for hint in (
                "company",
                "organization",
                "organizer",
                "issuer",
                "department",
                "机构",
                "部门",
            )
        ):
            return "organization"
        return "unknown"

    @staticmethod
    def _report(
        *,
        task_id: str,
        doc_id: str,
        schema_id: str,
        template_id: str,
        organized: list[dict[str, Any]],
        options: ContentOrganizationOptions | None,
        warnings: list[str],
        document_quality_flags: list[dict[str, Any]],
        tag_options: ContentOrganizationOptions,
    ) -> ContentOrganizationReport:
        content_tags = Counter(
            tag
            for chunk in organized
            for tag in chunk.get("tags", {}).get("content", [])
        )
        quality_tags = Counter(
            tag
            for chunk in organized
            for tag in chunk.get("tags", {}).get("quality", [])
        )
        quality_flags = Counter(
            flag
            for chunk in organized
            for flag in chunk.get("quality_flags", [])
        )
        token_estimates = [int(chunk.get("token_estimate", 0)) for chunk in organized]
        protected_blocks_count = sum(
            len(chunk.get("organization_trace", {}).get("protected_blocks", []))
            for chunk in organized
        )
        source_linked_count = sum(
            1
            for chunk in organized
            if chunk.get("source_block_ids") or chunk.get("source_links")
        )
        length_ok_count = sum(
            1
            for chunk in organized
            if "length_ok" in chunk.get("tags", {}).get("quality", [])
        )
        parent_chunk_count = sum(
            1 for chunk in organized if chunk.get("granularity") == "parent"
        )
        child_chunk_count = sum(
            1 for chunk in organized if chunk.get("granularity") == "child"
        )
        strategy = options.chunk_strategy if options else "legacy"
        return ContentOrganizationReport(
            task_id=task_id,
            doc_id=doc_id,
            chunk_count=len(organized),
            chunks_with_summary=sum(1 for chunk in organized if chunk.get("summary")),
            chunks_with_keywords=sum(1 for chunk in organized if chunk.get("keywords")),
            chunks_with_source_links=sum(1 for chunk in organized if chunk.get("source_links")),
            chunks_with_content_tags=sum(
                1
                for chunk in organized
                if chunk.get("tags", {}).get("content")
            ),
            chunks_with_quality_tags=sum(
                1
                for chunk in organized
                if chunk.get("tags", {}).get("quality")
            ),
            warnings=warnings,
            document_quality_flags=document_quality_flags,
            tag_rule_summary={
                "content_base_tag_count": len(
                    tag_options.tag_rules.content.base_tags
                ),
                "content_rule_count": len(tag_options.tag_rules.content.rules),
                "management_static_tag_count": len(
                    tag_options.tag_rules.management.static_tags
                ),
                "management_metadata_rule_count": len(
                    tag_options.tag_rules.management.metadata_rules
                ),
                "quality_builtin_rule_count": len(
                    tag_options.tag_rules.quality.enabled_builtin_rules
                ),
            },
            summary={
                "schema_id": schema_id,
                "template_id": template_id,
                "strategy": strategy,
                "options": options.model_dump(mode="json") if options else {},
                "chunk_count": len(organized),
                "parent_chunk_count": parent_chunk_count,
                "child_chunk_count": child_chunk_count or (
                    len(organized) if parent_chunk_count == 0 else 0
                ),
                "content_tag_counts": dict(sorted(content_tags.items())),
                "quality_tag_counts": dict(sorted(quality_tags.items())),
                "quality_flags_summary": dict(sorted(quality_flags.items())),
                "avg_token_estimate": round(sum(token_estimates) / len(token_estimates), 2)
                if token_estimates
                else 0,
                "min_token_estimate": min(token_estimates) if token_estimates else 0,
                "max_token_estimate": max(token_estimates) if token_estimates else 0,
                "length_ok_count": length_ok_count,
                "oversized_count": quality_tags.get("oversized_chunk", 0)
                + quality_tags.get("overlong_chunk", 0),
                "empty_chunk_count": quality_tags.get("empty_text", 0),
                "source_linked_count": source_linked_count,
                "protected_blocks_count": protected_blocks_count,
                "oversized_protected_blocks_count": quality_flags.get(
                    "oversized_protected_block",
                    0,
                ),
                "chunks": [
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "token_estimate": chunk.get("token_estimate", 0),
                        "quality_flags": chunk.get("quality_flags", []),
                        "source_block_ids": chunk.get("source_block_ids", []),
                    }
                    for chunk in organized
                ],
            },
        )
