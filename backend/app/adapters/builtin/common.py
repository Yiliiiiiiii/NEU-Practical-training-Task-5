from typing import Any

from app.schemas.external_uir import AdapterTraceItem, hash_payload
from app.schemas.uir import SourceAnchor, UIRBlock, UIRDocument, UIRSource


class BuiltinAdapterMixin:
    adapter_version: str
    known_schema_ids = {
        "contract_doc",
        "general_doc",
        "meeting_doc",
        "policy_doc",
        "procurement_doc",
    }

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
        target_block_id: str = "document",
        source_value_preview: str = "",
        confidence: float = 1.0,
    ) -> AdapterTraceItem:
        return AdapterTraceItem(
            external_path=external_path,
            canonical_path=canonical_path,
            target_block_id=target_block_id,
            conversion_rule=evidence,
            source_value_preview=source_value_preview[:160],
            strategy="rule",
            confidence=confidence,
            evidence=[evidence],
            review_required=False,
        )

    @staticmethod
    def _trace_coverage(trace_items: list[AdapterTraceItem], block_count: int) -> float:
        if block_count == 0:
            return 1.0
        covered_blocks = {
            item.canonical_path.split("]", 1)[0] + "]"
            for item in trace_items
            if item.canonical_path.startswith("blocks[")
        }
        return round(len(covered_blocks) / block_count, 4)

    @classmethod
    def _route_hints(cls, payload: dict[str, Any]) -> list[str]:
        values = [payload.get("schema_hint"), payload.get("document_type")]
        document = payload.get("document")
        if isinstance(document, dict):
            values.extend([document.get("schema_hint"), document.get("document_type")])
        return [
            value
            for value in values
            if isinstance(value, str) and value in cls.known_schema_ids
        ][:1]
