from typing import Any

from app.adapters.base import AdapterInput
from app.adapters.registry import build_default_registry
from app.schemas.external_uir import (
    AdapterReport,
    AdapterTraceItem,
    ExternalUIRPayload,
    ExternalUIRSource,
    hash_payload,
)
from app.schemas.uir import SourceAnchor, UIRBlock, UIRDocument, UIRSource


class ExternalUIRAdapterService:
    adapter_version = "external-uir-adapter-v1"

    def detect_dialect(self, payload: dict[str, Any]) -> str:
        selected = build_default_registry().select_adapter(AdapterInput(payload=payload))
        if selected.adapter_id is None:
            raise ValueError("unsupported external UIR dialect")
        return selected.adapter_id

    def adapt(
        self,
        external: ExternalUIRPayload,
        *,
        allow_llm: bool = False,
    ) -> tuple[UIRDocument, AdapterReport]:
        if allow_llm:
            raise ValueError("LLM suggestions are not implemented for external UIR adapter")

        result = build_default_registry().convert(
            AdapterInput(
                payload=external.payload,
                source_system=external.source.source_system,
                dialect_hint=external.source.source_format or "auto",
                options={"external_doc_id": external.external_doc_id},
            )
        )
        return result.standard_uir, result.adapter_report

    def adapt_from_dict(
        self,
        payload: dict[str, Any],
        *,
        source_system: str,
        allow_llm: bool = False,
    ) -> tuple[UIRDocument, AdapterReport]:
        source = ExternalUIRSource(source_system=source_system, source_format="auto")
        external = ExternalUIRPayload(
            external_doc_id=self._external_doc_id(payload),
            source=source,
            payload=payload,
        )
        return self.adapt(external, allow_llm=allow_llm)

    def _adapt_block_list(
        self,
        external: ExternalUIRPayload,
    ) -> tuple[UIRDocument, list[AdapterTraceItem], list[str]]:
        payload = external.payload
        items_key = next(
            key for key in ("chunks", "blocks", "items") if isinstance(payload.get(key), list)
        )
        items = payload[items_key]
        doc_id = external.external_doc_id or self._fallback_doc_id(payload)
        title = self._string_or_none(payload.get("title")) or doc_id
        trace_items = [
            self._trace("payload.id", "doc_id", "external document id preserved"),
            self._trace("payload.title", "metadata.title", "external title preserved"),
        ]
        blocks: list[UIRBlock] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            block_type = self._canonical_block_type(item.get("type"))
            text = self._string_or_none(item.get("text") or item.get("title"))
            attributes = {"external_path": f"payload.{items_key}[{index}]"}
            if "metadata" in item:
                attributes["metadata"] = item["metadata"]
            if "field" in item:
                attributes["field_name"] = item["field"]
            if block_type == "table":
                rows = item.get("rows") or item.get("table")
                if isinstance(rows, list):
                    attributes["rows"] = rows
                    trace_items.append(
                        self._trace(
                            f"payload.{items_key}[{index}].rows",
                            f"blocks[{len(blocks)}].attributes.rows",
                            "external table rows preserved",
                        )
                    )
            anchor = self._source_anchor(item)
            blocks.append(
                UIRBlock(
                    block_id=str(item.get("id") or f"b{len(blocks) + 1:03d}"),
                    type=block_type,
                    text=text,
                    source_anchor=anchor,
                    attributes=attributes,
                )
            )
            trace_items.append(
                self._trace(
                    f"payload.{items_key}[{index}].text",
                    f"blocks[{len(blocks) - 1}].text",
                    "external block text preserved",
                )
            )

        uir = self._document(
            doc_id=doc_id,
            source_system=external.source.source_system,
            title=title,
            source_url=self._string_or_none(payload.get("url")),
            blocks=blocks,
        )
        return uir, trace_items, []

    def _adapt_section_tree(
        self,
        external: ExternalUIRPayload,
    ) -> tuple[UIRDocument, list[AdapterTraceItem], list[str]]:
        document = external.payload["document"]
        doc_id = external.external_doc_id or self._fallback_doc_id(external.payload)
        title = self._string_or_none(document.get("name") or document.get("title")) or doc_id
        source = document.get("source") if isinstance(document.get("source"), dict) else {}
        blocks: list[UIRBlock] = []
        trace_items = [
            self._trace("payload.document.docNo", "doc_id", "external document id preserved"),
            self._trace("payload.document.name", "metadata.title", "external title preserved"),
        ]
        self._append_sections(
            sections=document.get("sections", []),
            base_path="payload.document.sections",
            blocks=blocks,
            trace_items=trace_items,
        )
        uir = self._document(
            doc_id=doc_id,
            source_system=external.source.source_system,
            title=title,
            source_url=self._string_or_none(source.get("url")),
            blocks=blocks,
        )
        return uir, trace_items, []

    def _append_sections(
        self,
        *,
        sections: list[Any],
        base_path: str,
        blocks: list[UIRBlock],
        trace_items: list[AdapterTraceItem],
        level: int = 1,
    ) -> None:
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            section_path = f"{base_path}[{index}]"
            heading = self._string_or_none(section.get("heading") or section.get("title"))
            if heading:
                blocks.append(
                    UIRBlock(
                        block_id=f"b{len(blocks) + 1:03d}",
                        type="heading",
                        level=level,
                        text=heading,
                        attributes={"external_path": section_path},
                    )
                )
                trace_items.append(
                    self._trace(
                        f"{section_path}.heading",
                        f"blocks[{len(blocks) - 1}].text",
                        "external section heading preserved",
                    )
                )
            for paragraph_index, paragraph in enumerate(section.get("paragraphs", [])):
                text = self._string_or_none(paragraph)
                if not text:
                    continue
                blocks.append(
                    UIRBlock(
                        block_id=f"b{len(blocks) + 1:03d}",
                        type="paragraph",
                        text=text,
                        attributes={
                            "external_path": f"{section_path}.paragraphs[{paragraph_index}]"
                        },
                    )
                )
                trace_items.append(
                    self._trace(
                        f"{section_path}.paragraphs[{paragraph_index}]",
                        f"blocks[{len(blocks) - 1}].text",
                        "external section paragraph preserved",
                    )
                )
            for table_index, table in enumerate(section.get("tables", [])):
                rows = table.get("rows") if isinstance(table, dict) else table
                if not isinstance(rows, list):
                    continue
                blocks.append(
                    UIRBlock(
                        block_id=f"b{len(blocks) + 1:03d}",
                        type="table",
                        attributes={
                            "rows": rows,
                            "external_path": f"{section_path}.tables[{table_index}]",
                        },
                    )
                )
                trace_items.append(
                    self._trace(
                        f"{section_path}.tables[{table_index}].rows",
                        f"blocks[{len(blocks) - 1}].attributes.rows",
                        "external section table rows preserved",
                    )
                )
            children = section.get("children")
            if isinstance(children, list):
                self._append_sections(
                    sections=children,
                    base_path=f"{section_path}.children",
                    blocks=blocks,
                    trace_items=trace_items,
                    level=level + 1,
                )

    def _document(
        self,
        *,
        doc_id: str,
        source_system: str,
        title: str,
        source_url: str | None,
        blocks: list[UIRBlock],
    ) -> UIRDocument:
        metadata: dict[str, Any] = {
            "title": title,
            "source_system": source_system,
            "external_uir_adapter_version": self.adapter_version,
        }
        if source_url:
            metadata["source_url"] = source_url
        return UIRDocument(
            uir_version="1.0",
            doc_id=doc_id,
            source=UIRSource(
                source_type="external_uir",
                source_name=source_system,
                upstream_agents=[source_system],
            ),
            metadata=metadata,
            blocks=blocks,
            assets=[],
            normalization_records=[],
        )

    @staticmethod
    def _external_doc_id(payload: dict[str, Any]) -> str | None:
        if isinstance(payload.get("id"), str):
            return payload["id"]
        document = payload.get("document")
        if isinstance(document, dict):
            doc_no = document.get("docNo") or document.get("id")
            if isinstance(doc_no, str):
                return doc_no
        return None

    @staticmethod
    def _fallback_doc_id(payload: dict[str, Any]) -> str:
        return hash_payload(payload).replace("sha256:", "external_")[:21]

    @staticmethod
    def _canonical_block_type(value: Any) -> str:
        if value in {"title", "heading", "header"}:
            return "heading"
        if value in {"table", "grid"}:
            return "table"
        if value in {"list", "paragraph"}:
            return str(value)
        return "paragraph"

    @staticmethod
    def _source_anchor(item: dict[str, Any]) -> SourceAnchor | None:
        page = item.get("page")
        bbox = item.get("bbox")
        if isinstance(page, int) or isinstance(bbox, list):
            return SourceAnchor(
                page=page if isinstance(page, int) else None,
                bbox=bbox if isinstance(bbox, list) else None,
            )
        return None

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _trace(
        external_path: str,
        canonical_path: str,
        evidence: str,
        *,
        confidence: float = 1.0,
    ) -> AdapterTraceItem:
        return AdapterTraceItem(
            external_path=external_path,
            canonical_path=canonical_path,
            target_block_id=canonical_path,
            conversion_rule=evidence,
            source_value_preview="",
            strategy="rule",
            confidence=confidence,
            evidence=[evidence],
            review_required=False,
        )
