import re
from collections import Counter
from typing import Any

from app.schemas.canonical import CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.content_organization import (
    ChunkTags,
    ContentOrganizationReport,
    EntityTag,
    OrganizedChunk,
    SourceLink,
)
from app.schemas.reports import MappingReport, ValidationReport
from app.schemas.target_schema import TargetField, TargetSchema


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
    CONTENT_TAG_RULES = {
        "policy_doc": {
            "scope": ["适用", "范围", "对象", "适用于"],
            "responsibility": ["职责", "负责", "部门", "责任"],
            "procedure": ["流程", "步骤", "审批", "执行"],
            "compliance": ["合规", "禁止", "不得", "必须", "应当"],
        },
        "contract_doc": {
            "party": ["甲方", "乙方", "双方", "委托方", "受托方"],
            "amount": ["金额", "价款", "费用", "付款", "结算"],
            "term": ["期限", "生效", "终止", "履行"],
            "liability": ["违约", "责任", "赔偿"],
        },
        "meeting_doc": {
            "attendee": ["参会", "出席", "列席"],
            "decision": ["决定", "决议", "通过"],
            "action_item": ["任务", "跟进", "负责人", "截止"],
        },
        "general_doc": {
            "overview": ["概述", "简介", "背景"],
            "requirement": ["要求", "标准", "指标"],
            "result": ["结果", "结论", "产出"],
        },
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
    ) -> tuple[list[dict[str, Any]], ContentOrganizationReport]:
        warnings: list[str] = []
        if not chunks:
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
        for index, chunk in enumerate(chunks):
            text = str(chunk.get("text") or "")
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
            )
            tags = ChunkTags(
                content=self._content_tags(text, schema_id),
                management=self._management_tags(
                    task_id=task_id,
                    doc_id=doc_id,
                    schema=schema,
                    template_id=template_id,
                    template_version=template_version,
                    index=index,
                ),
                quality=self._quality_tags(
                    text=text,
                    token_estimate=self.estimate_tokens(text),
                    source_block_ids=source_block_ids,
                    source_links=source_links,
                    summary=summary,
                    keywords=keywords,
                    mapping_report=mapping_report,
                    validation_report=validation_report,
                ),
            )
            organized_chunk = OrganizedChunk(
                chunk_id=str(chunk.get("chunk_id") or f"chunk_{doc_id}_{index:04d}"),
                doc_id=doc_id,
                task_id=task_id,
                index=index,
                text=text,
                token_estimate=self.estimate_tokens(text),
                title_path=list(chunk.get("title_path", [])),
                source_block_ids=source_block_ids,
                source_links=source_links,
                tags=tags,
                keywords=keywords,
                summary=summary,
                entity_tags=self._chunk_entity_tags(
                    text=text,
                    source_block_ids=source_block_ids,
                    entity_candidates=entity_candidates,
                ),
                organization_trace={
                    "summary_strategy": "first_sentence_or_prefix",
                    "keyword_strategy": "frequency_with_stopwords",
                    "tag_strategy": "schema_and_rule_based",
                    "source_link_strategy": "canonical_block_anchor_or_path",
                },
            )
            organized.append(organized_chunk.model_dump(mode="json"))

        report = self._report(
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            template_id=template_id,
            organized=organized,
            warnings=warnings,
        )
        return organized, report

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
    def _content_tags(cls, text: str, schema_id: str) -> list[str]:
        tags = {schema_id.removesuffix("_doc") or "general"}
        rules = cls.CONTENT_TAG_RULES.get(schema_id, {})
        for tag, needles in rules.items():
            if any(needle in text for needle in needles):
                tags.add(tag)
        if not tags:
            tags.add("general")
        return sorted(tags)

    @staticmethod
    def _management_tags(
        *,
        task_id: str,
        doc_id: str,
        schema: TargetSchema,
        template_id: str,
        template_version: str | None,
        index: int,
    ) -> list[str]:
        tags = [
            f"schema:{schema.schema_id}",
            f"schema_version:{schema.version}",
            f"template:{template_id}",
            f"doc:{doc_id}",
            f"task:{task_id}",
            f"chunk_index:{index}",
        ]
        if template_version:
            tags.append(f"template_version:{template_version}")
        return sorted(tags)

    @classmethod
    def _quality_tags(
        cls,
        *,
        text: str,
        token_estimate: int,
        source_block_ids: list[str],
        source_links: list[SourceLink],
        summary: str,
        keywords: list[str],
        mapping_report: MappingReport,
        validation_report: ValidationReport | None,
    ) -> list[str]:
        tags: set[str] = set()
        if source_block_ids:
            tags.add("source_linked")
        if source_links:
            tags.add("anchor_linked")
        if validation_report is not None:
            if any(issue.level == "error" for issue in validation_report.issues):
                tags.add("validation_has_errors")
            else:
                tags.add("validation_passed")
        if mapping_report.review_required_items:
            tags.add("mapping_review_required")
        if not text:
            tags.add("empty_text")
        if token_estimate > 1000:
            tags.add("overlong_chunk")
        if 0 < token_estimate < 10:
            tags.add("short_chunk")
        if summary:
            tags.add("summarized")
        if keywords:
            tags.add("keyworded")
        return sorted(tags)

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
        warnings: list[str],
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
        token_estimates = [int(chunk.get("token_estimate", 0)) for chunk in organized]
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
            summary={
                "schema_id": schema_id,
                "template_id": template_id,
                "content_tag_counts": dict(sorted(content_tags.items())),
                "quality_tag_counts": dict(sorted(quality_tags.items())),
                "avg_token_estimate": round(sum(token_estimates) / len(token_estimates), 2)
                if token_estimates
                else 0,
            },
        )
