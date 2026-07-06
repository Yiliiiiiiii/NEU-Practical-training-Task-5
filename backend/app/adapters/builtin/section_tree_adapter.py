from typing import Any

from app.adapters.base import AdapterInput, AdapterResult, ExternalUirAdapter
from app.adapters.builtin.common import BuiltinAdapterMixin
from app.schemas.adapter import AdapterCapability
from app.schemas.external_uir import AdapterReport, AdapterTraceItem, hash_payload
from app.schemas.uir import UIRBlock


class SectionTreeAdapter(BuiltinAdapterMixin, ExternalUirAdapter):
    adapter_version = "section-tree-adapter-v1"
    capability = AdapterCapability(
        adapter_id="section_tree",
        adapter_version=adapter_version,
        supported_dialects=["section-tree", "section_tree"],
        source_systems=["topic11", "generic", "external"],
        supports_tables=True,
        supports_sections=True,
        supports_pages=False,
        supports_bbox=False,
        requires_llm=False,
        description="Converts nested External UIR section trees into standard UIR blocks.",
    )

    def can_handle(self, adapter_input: AdapterInput) -> float:
        document = adapter_input.payload.get("document")
        if isinstance(document, dict) and isinstance(document.get("sections"), list):
            return 0.95
        return 0.0

    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        payload = adapter_input.payload
        document = payload["document"]
        external_doc_id = adapter_input.options.get("external_doc_id")
        doc_id = (
            external_doc_id
            if isinstance(external_doc_id, str) and external_doc_id
            else self._external_doc_id(payload) or self._fallback_doc_id(payload)
        )
        title = self._string_or_none(document.get("name") or document.get("title")) or doc_id
        source = document.get("source") if isinstance(document.get("source"), dict) else {}
        blocks: list[UIRBlock] = []
        trace_items = [
            self._trace(
                "payload.document.docNo",
                "doc_id",
                "external document id preserved",
                source_value_preview=doc_id,
            ),
            self._trace(
                "payload.document.name",
                "metadata.title",
                "external title preserved",
                source_value_preview=title,
            ),
        ]
        self._append_sections(
            sections=document.get("sections", []),
            base_path="payload.document.sections",
            blocks=blocks,
            trace_items=trace_items,
        )
        uir = self._document(
            doc_id=doc_id,
            source_system=adapter_input.source_system,
            title=title,
            source_url=self._string_or_none(source.get("url")),
            blocks=blocks,
        )
        report = AdapterReport(
            adapter_id=self.capability.adapter_id,
            adapter_version=self.adapter_version,
            source_system=adapter_input.source_system,
            external_doc_id=doc_id,
            generated_doc_id=uir.doc_id,
            status="passed",
            trace_items=trace_items,
            trace_coverage=self._trace_coverage(trace_items, len(blocks)),
            block_count=len(blocks),
            table_count=sum(1 for block in blocks if block.type == "table"),
            route_hints=self._route_hints(payload),
            warning_count=0,
            error_count=0,
            warnings=[],
            errors=[],
            raw_payload_hash=hash_payload(payload),
            dialect="section-tree",
            detected_dialect="section-tree",
        )
        return AdapterResult(
            standard_uir=uir,
            adapter_report=report,
            warnings=report.warnings,
            errors=report.errors,
        )

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
            self._append_heading(
                section=section,
                section_path=section_path,
                blocks=blocks,
                trace_items=trace_items,
                level=level,
            )
            self._append_paragraphs(
                section=section,
                section_path=section_path,
                blocks=blocks,
                trace_items=trace_items,
            )
            self._append_tables(
                section=section,
                section_path=section_path,
                blocks=blocks,
                trace_items=trace_items,
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

    def _append_heading(
        self,
        *,
        section: dict,
        section_path: str,
        blocks: list[UIRBlock],
        trace_items: list[AdapterTraceItem],
        level: int,
    ) -> None:
        heading = self._string_or_none(section.get("heading") or section.get("title"))
        if not heading:
            return
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
                target_block_id=blocks[-1].block_id,
                source_value_preview=heading,
            )
        )

    def _append_paragraphs(
        self,
        *,
        section: dict,
        section_path: str,
        blocks: list[UIRBlock],
        trace_items: list[AdapterTraceItem],
    ) -> None:
        for paragraph_index, paragraph in enumerate(section.get("paragraphs", [])):
            text = self._string_or_none(paragraph)
            if not text:
                continue
            blocks.append(
                UIRBlock(
                    block_id=f"b{len(blocks) + 1:03d}",
                    type="paragraph",
                    text=text,
                    attributes={"external_path": f"{section_path}.paragraphs[{paragraph_index}]"},
                )
            )
            trace_items.append(
                self._trace(
                    f"{section_path}.paragraphs[{paragraph_index}]",
                    f"blocks[{len(blocks) - 1}].text",
                    "external section paragraph preserved",
                    target_block_id=blocks[-1].block_id,
                    source_value_preview=text,
                )
            )

    def _append_tables(
        self,
        *,
        section: dict,
        section_path: str,
        blocks: list[UIRBlock],
        trace_items: list[AdapterTraceItem],
    ) -> None:
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
                    target_block_id=blocks[-1].block_id,
                    source_value_preview=repr(rows),
                )
            )
