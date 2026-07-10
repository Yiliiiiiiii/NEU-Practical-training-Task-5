from __future__ import annotations

import re
from typing import Any

from app.schemas.canonical import CanonicalModel
from app.schemas.content_organization import (
    ContentOrganizationOptions,
    ContentTagRule,
    SourceLink,
)
from app.schemas.reports import MappingReport, ReportIssue, ValidationReport
from app.schemas.target_schema import TargetSchema


class TagRuleService:
    def content_tags(
        self,
        *,
        text: str,
        title_path: list[str],
        block_types: list[str],
        source_block_ids: list[str],
        schema_id: str,
        options: ContentOrganizationOptions,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        config = options.tag_rules.content
        tags: set[str] = set()
        traces: list[dict[str, Any]] = []
        base_tags = config.base_tags or [schema_id.removesuffix("_doc") or schema_id]
        for tag in base_tags:
            tags.add(tag)
            traces.append(
                self._trace(
                    tag=tag,
                    rule_id=(
                        f"content:base:{tag}"
                        if config.base_tags
                        else "content:generic_schema"
                    ),
                    evidence=(
                        "configured base tag"
                        if config.base_tags
                        else f"normalized schema_id={schema_id}"
                    ),
                    source_block_ids=source_block_ids,
                )
            )
        for rule in config.rules:
            matched, evidence = self._content_rule_matches(
                rule,
                text=text,
                title_path=title_path,
                block_types=block_types,
            )
            if not matched:
                continue
            tags.add(rule.tag)
            traces.append(
                self._trace(
                    tag=rule.tag,
                    rule_id=rule.rule_id or f"content:{rule.tag}",
                    evidence=evidence,
                    source_block_ids=source_block_ids,
                )
            )
        return sorted(tags), self._dedupe_traces(traces)

    def management_tags(
        self,
        *,
        canonical: CanonicalModel,
        schema: TargetSchema,
        template_id: str,
        template_version: str | None,
        source_block_ids: list[str],
        options: ContentOrganizationOptions,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        config = options.tag_rules.management
        tags = set(config.static_tags)
        traces = [
            self._trace(
                tag=tag,
                rule_id=f"management:static:{tag}",
                evidence="configured static management tag",
                source_block_ids=source_block_ids,
            )
            for tag in config.static_tags
        ]
        context = {
            "document_metadata": canonical.doc_meta.get("document_metadata", {}),
            "schema": {
                "schema_id": schema.schema_id,
                "version": schema.version,
            },
            "package": {
                "template_id": template_id,
                "template_version": template_version,
            },
        }
        for rule in config.metadata_rules:
            value = self._resolve_path(context, rule.source_path)
            if value is None and rule.omit_if_missing:
                continue
            if value is None:
                value = ""
            tag = rule.tag_template.replace("{value}", self._format_value(value))
            tags.add(tag)
            related_fields = (
                [rule.source_path.removeprefix("document_metadata.")]
                if rule.source_path.startswith("document_metadata.")
                else []
            )
            traces.append(
                self._trace(
                    tag=tag,
                    rule_id=rule.rule_id or f"management:{rule.source_path}",
                    evidence=f"{rule.source_path}={self._format_value(value)}",
                    source_block_ids=source_block_ids,
                    related_field_ids=related_fields,
                )
            )
        return sorted(tags), self._dedupe_traces(traces)

    def quality_tags(
        self,
        *,
        chunk_id: str,
        text: str,
        token_estimate: int,
        source_block_ids: list[str],
        source_links: list[SourceLink],
        summary: str,
        keywords: list[str],
        quality_flags: list[str],
        entity_tags: list[dict[str, Any]],
        canonical: CanonicalModel,
        mapping_report: MappingReport,
        validation_report: ValidationReport | None,
        options: ContentOrganizationOptions,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        enabled = set(options.tag_rules.quality.enabled_builtin_rules)
        tags: set[str] = set()
        traces: list[dict[str, Any]] = []

        def add(
            tag: str,
            evidence: str,
            *,
            related_fields: list[str] | None = None,
            related_codes: list[str] | None = None,
        ) -> None:
            if tag not in enabled:
                return
            tags.add(tag)
            traces.append(
                self._trace(
                    tag=tag,
                    rule_id=f"quality:{tag}",
                    evidence=evidence,
                    source_block_ids=source_block_ids,
                    related_field_ids=related_fields or [],
                    related_issue_codes=related_codes or [],
                )
            )

        if source_block_ids:
            add("source_linked", "chunk declares source block ids")
        else:
            add("source_unlinked", "chunk has no source block ids")
        if source_links and all(link.source_path for link in source_links):
            add("anchor_linked", "all source links resolve to canonical blocks")
        if not text:
            add("empty_text", "chunk text is empty")
        elif token_estimate < options.min_tokens:
            add("short_chunk", f"token_estimate={token_estimate}")
        elif token_estimate > options.max_tokens:
            add("overlong_chunk", f"token_estimate={token_estimate}")
        else:
            add("length_ok", f"token_estimate={token_estimate}")
        if summary:
            add("summarized", "deterministic chunk summary is present")
        else:
            add("summary_missing", "chunk summary is missing")
        if keywords:
            add("keyworded", "deterministic chunk keywords are present")
        else:
            add("keyword_missing", "chunk keywords are missing")
        if "oversized_protected_block" in quality_flags:
            add("oversized_protected_block", "protected block exceeds max_tokens")

        related_mapping = self._localized_mapping_items(
            mapping_report.review_required_items,
            canonical=canonical,
            source_block_ids=source_block_ids,
        )
        if related_mapping:
            add(
                "mapping_review_required",
                "mapping review item intersects chunk sources",
                related_fields=sorted(
                    {
                        str(item.get("target_field_id"))
                        for item in related_mapping
                        if item.get("target_field_id")
                    }
                ),
                related_codes=sorted(
                    {
                        str(flag)
                        for item in related_mapping
                        for flag in item.get("risk_flags", [])
                        if flag
                    }
                ),
            )

        related_issues = self._localized_validation_issues(
            validation_report,
            canonical=canonical,
            chunk_id=chunk_id,
            source_block_ids=source_block_ids,
        )
        if related_issues:
            add(
                "validation_error",
                "validation issue intersects chunk sources",
                related_fields=sorted(
                    {issue.field_id for issue in related_issues if issue.field_id}
                ),
                related_codes=sorted(
                    {issue.code for issue in related_issues if issue.code}
                ),
            )
        if entity_tags:
            if any(item.get("link_status") == "linked" for item in entity_tags):
                add("entity_linked", "chunk contains a linked upstream entity")
            if any(item.get("link_status") in {"unlinked", "nil"} for item in entity_tags):
                add("entity_unlinked", "chunk contains an unlinked upstream entity")
        return sorted(tags), self._dedupe_traces(traces)

    def document_quality_flags(
        self,
        *,
        chunks: list[dict[str, Any]],
        canonical: CanonicalModel,
        mapping_report: MappingReport,
        validation_report: ValidationReport | None,
        options: ContentOrganizationOptions,
    ) -> list[dict[str, Any]]:
        enabled = set(options.tag_rules.quality.enabled_builtin_rules)
        flags: list[dict[str, Any]] = []
        chunk_ids = {str(chunk.get("chunk_id")) for chunk in chunks}
        for item in mapping_report.review_required_items:
            if "mapping_review_required" not in enabled:
                break
            if self._mapping_blocks(item, canonical):
                continue
            flags.append(
                self._trace(
                    tag="mapping_review_required",
                    rule_id="quality:mapping_review_required",
                    scope="document",
                    evidence=str(
                        item.get("review_required_reason")
                        or "mapping review item cannot be localized"
                    ),
                    related_field_ids=(
                        [str(item["target_field_id"])]
                        if item.get("target_field_id")
                        else []
                    ),
                    related_issue_codes=[
                        str(flag) for flag in item.get("risk_flags", []) if flag
                    ],
                )
            )
        if validation_report is not None and "validation_error" in enabled:
            for issue in validation_report.issues:
                if issue.level != "error":
                    continue
                if self._validation_blocks(issue, canonical):
                    continue
                if issue.path is not None and issue.path in chunk_ids:
                    continue
                flags.append(
                    self._trace(
                        tag="validation_error",
                        rule_id="quality:validation_error",
                        scope="document",
                        evidence=issue.message,
                        related_field_ids=[issue.field_id] if issue.field_id else [],
                        related_issue_codes=[issue.code] if issue.code else [],
                    )
                )
        return self._dedupe_traces(flags)

    @staticmethod
    def _content_rule_matches(
        rule: ContentTagRule,
        *,
        text: str,
        title_path: list[str],
        block_types: list[str],
    ) -> tuple[bool, str]:
        body = text if rule.case_sensitive else text.lower()
        title = " ".join(title_path)
        title = title if rule.case_sensitive else title.lower()

        def normalized(values: list[str]) -> list[str]:
            return values if rule.case_sensitive else [value.lower() for value in values]

        any_terms = normalized(rule.any_terms)
        all_terms = normalized(rule.all_terms)
        none_terms = normalized(rule.none_terms)
        title_terms = normalized(rule.title_terms)
        if any_terms and not any(term in body for term in any_terms):
            return False, ""
        if all_terms and not all(term in body for term in all_terms):
            return False, ""
        if none_terms and any(term in body for term in none_terms):
            return False, ""
        if title_terms and not any(term in title for term in title_terms):
            return False, ""
        if rule.block_types and not set(rule.block_types).intersection(block_types):
            return False, ""
        matched_terms = sorted(
            {term for term in [*any_terms, *all_terms, *title_terms] if term in f"{body} {title}"}
        )
        evidence = ", ".join(matched_terms) if matched_terms else "configured predicates matched"
        return True, evidence

    @classmethod
    def _localized_mapping_items(
        cls,
        items: list[dict[str, Any]],
        *,
        canonical: CanonicalModel,
        source_block_ids: list[str],
    ) -> list[dict[str, Any]]:
        chunk_sources = set(source_block_ids)
        return [
            item
            for item in items
            if chunk_sources.intersection(cls._mapping_blocks(item, canonical))
        ]

    @classmethod
    def _localized_validation_issues(
        cls,
        report: ValidationReport | None,
        *,
        canonical: CanonicalModel,
        chunk_id: str,
        source_block_ids: list[str],
    ) -> list[ReportIssue]:
        if report is None:
            return []
        chunk_sources = set(source_block_ids)
        return [
            issue
            for issue in report.issues
            if issue.level == "error"
            and (
                bool(chunk_sources.intersection(cls._validation_blocks(issue, canonical)))
                or issue.path == chunk_id
            )
        ]

    @classmethod
    def _mapping_blocks(
        cls, item: dict[str, Any], canonical: CanonicalModel
    ) -> set[str]:
        blocks = {str(value) for value in item.get("source_blocks", []) if value}
        target_field_id = item.get("target_field_id")
        if target_field_id in canonical.fields:
            blocks.update(canonical.fields[str(target_field_id)].source_blocks)
        source_path = item.get("source_path")
        if not isinstance(source_path, str):
            source_field = item.get("source_field")
            if isinstance(source_field, dict):
                source_path = source_field.get("source_path")
        blocks.update(cls._blocks_from_path(source_path, canonical))
        return blocks

    @classmethod
    def _validation_blocks(
        cls, issue: ReportIssue, canonical: CanonicalModel
    ) -> set[str]:
        blocks: set[str] = set()
        if issue.field_id in canonical.fields:
            blocks.update(canonical.fields[str(issue.field_id)].source_blocks)
        blocks.update(cls._blocks_from_path(issue.path, canonical))
        return blocks

    @staticmethod
    def _blocks_from_path(path: Any, canonical: CanonicalModel) -> set[str]:
        if not isinstance(path, str):
            return set()
        block_ids = {block.block_id for block in canonical.blocks}
        if path in block_ids:
            return {path}
        match = re.search(r"blocks\[(\d+)]", path)
        if match:
            index = int(match.group(1))
            if 0 <= index < len(canonical.blocks):
                return {canonical.blocks[index].block_id}
        return {block_id for block_id in block_ids if block_id in path}

    @staticmethod
    def _resolve_path(context: dict[str, Any], path: str) -> Any:
        value: Any = context
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str | int | float):
            return str(value)
        return ""

    @staticmethod
    def _trace(
        *,
        tag: str,
        rule_id: str,
        evidence: str,
        scope: str = "chunk",
        source_block_ids: list[str] | None = None,
        related_field_ids: list[str] | None = None,
        related_issue_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "tag": tag,
            "rule_id": rule_id,
            "scope": scope,
            "evidence": evidence,
            "source_block_ids": sorted(set(source_block_ids or [])),
            "related_field_ids": sorted(set(related_field_ids or [])),
            "related_issue_codes": sorted(set(related_issue_codes or [])),
        }

    @staticmethod
    def _dedupe_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keyed = {
            (
                trace["tag"],
                trace["rule_id"],
                trace["scope"],
                trace["evidence"],
                tuple(trace["source_block_ids"]),
                tuple(trace["related_field_ids"]),
                tuple(trace["related_issue_codes"]),
            ): trace
            for trace in traces
        }
        return [keyed[key] for key in sorted(keyed)]
