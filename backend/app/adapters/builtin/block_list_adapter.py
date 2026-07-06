from app.adapters.base import AdapterInput, AdapterResult, ExternalUirAdapter
from app.adapters.builtin.common import BuiltinAdapterMixin
from app.schemas.adapter import AdapterCapability
from app.schemas.external_uir import AdapterReport, AdapterTraceItem, hash_payload
from app.schemas.uir import UIRBlock


class BlockListAdapter(BuiltinAdapterMixin, ExternalUirAdapter):
    adapter_version = "block-list-adapter-v1"
    capability = AdapterCapability(
        adapter_id="block_list",
        adapter_version=adapter_version,
        supported_dialects=["block-list", "block_list"],
        source_systems=["topic11", "generic", "external"],
        supports_tables=True,
        supports_sections=False,
        supports_pages=True,
        supports_bbox=True,
        requires_llm=False,
        description="Converts flat External UIR block/chunk/item lists into standard UIR.",
    )

    def can_handle(self, adapter_input: AdapterInput) -> float:
        if any(isinstance(adapter_input.payload.get(key), list) for key in self._item_keys()):
            return 0.95
        return 0.0

    def convert(self, adapter_input: AdapterInput) -> AdapterResult:
        payload = adapter_input.payload
        items_key = next(
            key for key in self._item_keys() if isinstance(payload.get(key), list)
        )
        items = payload[items_key]
        external_doc_id = adapter_input.options.get("external_doc_id")
        doc_id = (
            external_doc_id
            if isinstance(external_doc_id, str) and external_doc_id
            else self._external_doc_id(payload) or self._fallback_doc_id(payload)
        )
        title = self._string_or_none(payload.get("title")) or doc_id
        warnings = self._warnings(payload, items_key, items)
        trace_items = [
            self._trace(
                "payload.id",
                "doc_id",
                "external document id preserved",
                source_value_preview=doc_id,
            ),
            self._trace(
                "payload.title",
                "metadata.title",
                "external title preserved",
                source_value_preview=title,
            ),
        ]
        blocks: list[UIRBlock] = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            self._append_item(
                item=item,
                index=index,
                items_key=items_key,
                blocks=blocks,
                trace_items=trace_items,
            )

        uir = self._document(
            doc_id=doc_id,
            source_system=adapter_input.source_system,
            title=title,
            source_url=self._string_or_none(payload.get("url")),
            blocks=blocks,
        )
        report = self._report(
            source_system=adapter_input.source_system,
            payload=payload,
            external_doc_id=doc_id,
            generated_doc_id=uir.doc_id,
            trace_items=trace_items,
            block_count=len(blocks),
            table_count=sum(1 for block in blocks if block.type == "table"),
            warnings=warnings,
            errors=[],
        )
        return AdapterResult(
            standard_uir=uir,
            adapter_report=report,
            warnings=report.warnings,
            errors=report.errors,
        )

    def _append_item(
        self,
        *,
        item: dict,
        index: int,
        items_key: str,
        blocks: list[UIRBlock],
        trace_items: list[AdapterTraceItem],
    ) -> None:
        block_type = self._canonical_block_type(item.get("type"))
        text = self._string_or_none(item.get("text") or item.get("title"))
        block_id = str(item.get("id") or f"b{len(blocks) + 1:03d}")
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
                        target_block_id=block_id,
                        source_value_preview=repr(rows),
                    )
                )
        blocks.append(
            UIRBlock(
                block_id=block_id,
                type=block_type,
                text=text,
                source_anchor=self._source_anchor(item),
                attributes=attributes,
            )
        )
        trace_items.append(
            self._trace(
                    f"payload.{items_key}[{index}].text",
                    f"blocks[{len(blocks) - 1}].text",
                    "external block text preserved",
                    target_block_id=block_id,
                    source_value_preview=text or "",
                )
            )

    def _report(
        self,
        *,
        source_system: str,
        payload: dict,
        external_doc_id: str | None,
        generated_doc_id: str,
        trace_items: list[AdapterTraceItem],
        block_count: int,
        table_count: int,
        warnings: list[str],
        errors: list[str],
    ) -> AdapterReport:
        return AdapterReport(
            adapter_id=self.capability.adapter_id,
            adapter_version=self.adapter_version,
            source_system=source_system,
            external_doc_id=external_doc_id,
            generated_doc_id=generated_doc_id,
            status="review_required" if self._requires_review(warnings) else "passed",
            trace_items=trace_items,
            trace_coverage=self._trace_coverage(trace_items, block_count),
            block_count=block_count,
            table_count=table_count,
            route_hints=self._route_hints(payload),
            warning_count=len(warnings),
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            raw_payload_hash=hash_payload(payload),
            dialect="block-list",
            detected_dialect="block-list",
        )

    @staticmethod
    def _requires_review(warnings: list[str]) -> bool:
        return any(
            warning != "missing optional metadata: url" for warning in warnings
        )

    @staticmethod
    def _item_keys() -> tuple[str, str, str]:
        return ("chunks", "blocks", "items")

    @classmethod
    def _warnings(
        cls,
        payload: dict,
        items_key: str,
        items: list,
    ) -> list[str]:
        warnings: list[str] = []
        for key in ("id", "title", "url"):
            if not payload.get(key):
                warnings.append(f"missing optional metadata: {key}")
        allowed_payload = {
            "id",
            "title",
            "url",
            items_key,
            "schema_hint",
            "document_type",
        }
        unknown_payload = sorted(set(payload) - allowed_payload)
        if unknown_payload:
            warnings.append(
                "unknown top-level fields: " + ", ".join(unknown_payload)
            )
        allowed_item = {
            "id",
            "type",
            "text",
            "title",
            "metadata",
            "field",
            "rows",
            "table",
            "page",
            "bbox",
        }
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                warnings.append(f"{items_key}[{index}] is not an object")
                continue
            block_type = cls._canonical_block_type(item.get("type"))
            if block_type != "table" and not cls._string_or_none(
                item.get("text") or item.get("title")
            ):
                warnings.append(f"{items_key}[{index}] has empty text")
            unknown_item = sorted(set(item) - allowed_item)
            if unknown_item:
                warnings.append(
                    f"{items_key}[{index}] unknown fields: "
                    + ", ".join(unknown_item)
                )
        return warnings
