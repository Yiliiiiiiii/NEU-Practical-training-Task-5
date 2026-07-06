import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import Any

from app.schemas.schema_draft import FieldCandidate, FieldDiscoveryResult
from app.schemas.uir import UIRDocument


class FieldDiscoveryService:
    LABEL_ALIASES = {
        "项目名称": "project_name",
        "采购项目名称": "project_name",
        "标的名称": "project_name",
        "会议时间": "meeting_date",
        "会议日期": "meeting_date",
        "预算金额": "budget_amount",
        "采购预算": "budget_amount",
        "中标金额": "award_amount",
        "成交金额": "award_amount",
        "采购人": "purchaser",
        "采购单位": "purchaser",
        "招标人": "purchaser",
        "主持人": "host",
        "参会人员": "attendees",
        "联系人": "contact",
        "成文日期": "written_date",
        "发布日期": "publish_date",
        "retrieved_at": "retrieved_at",
    }
    RISK_FLAGS = {
        "budget_amount": ["budget_amount_not_award_amount"],
        "host": ["host_not_attendee"],
        "contact": ["contact_not_attendee"],
        "written_date": ["written_date_not_publish_date"],
        "retrieved_at": ["retrieved_at_not_effective_date"],
    }
    COLON_PATTERN = re.compile(
        r"(?P<label>[A-Za-z_][A-Za-z0-9_ ]{1,31}|[\u4e00-\u9fff]{2,24})"
        r"\s*[:：]\s*(?P<value>[^\n；;]+)"
    )
    DATE_PATTERN = re.compile(
        r"(?:19|20)\d{2}(?:[-/.年]\d{1,2})(?:[-/.月]\d{1,2})?日?"
    )
    AMOUNT_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:元|万元|亿元|CNY|RMB)", re.IGNORECASE)

    def discover(self, documents: list[UIRDocument]) -> FieldDiscoveryResult:
        if not documents:
            raise ValueError("at least one sample document is required")
        observations: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"labels": set(), "values": [], "paths": set(), "docs": set()}
        )
        for document in documents:
            self._collect_document(document, observations)

        candidates = [
            self._candidate(field_name, data, len(documents))
            for field_name, data in observations.items()
            if data["paths"]
        ]
        candidates.sort(key=lambda item: (-item.frequency, item.field_name))
        return FieldDiscoveryResult(
            sample_count=len(documents),
            field_candidates=candidates,
            warnings=[],
            llm_auto_accepted_count=0,
        )

    def _collect_document(
        self,
        document: UIRDocument,
        observations: dict[str, dict[str, Any]],
    ) -> None:
        for key, value in document.metadata.items():
            if key == "title":
                continue
            self._observe(
                observations,
                label=key,
                value=value,
                path=f"{document.doc_id}.metadata.{key}",
                doc_id=document.doc_id,
            )
        for index, block in enumerate(document.blocks):
            field_name = block.attributes.get("field_name")
            if isinstance(field_name, str):
                self._observe(
                    observations,
                    label=field_name,
                    value=block.text,
                    path=f"{document.doc_id}.blocks[{index}].attributes.field_name",
                    doc_id=document.doc_id,
                )
            rows = block.attributes.get("rows")
            if isinstance(rows, list):
                self._collect_rows(
                    document.doc_id,
                    index,
                    rows,
                    observations,
                )
            if block.text:
                self._collect_colon_patterns(
                    document.doc_id,
                    index,
                    block.text,
                    observations,
                )

    def _collect_rows(
        self,
        doc_id: str,
        block_index: int,
        rows: list[Any],
        observations: dict[str, dict[str, Any]],
    ) -> None:
        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) < 2:
                continue
            label, value = row[0], row[1]
            if not isinstance(label, str):
                continue
            self._observe(
                observations,
                label=label,
                value=value,
                path=f"{doc_id}.blocks[{block_index}].attributes.rows[{row_index}]",
                doc_id=doc_id,
            )

    def _collect_colon_patterns(
        self,
        doc_id: str,
        block_index: int,
        text: str,
        observations: dict[str, dict[str, Any]],
    ) -> None:
        for match in self.COLON_PATTERN.finditer(text):
            self._observe(
                observations,
                label=match.group("label"),
                value=match.group("value").strip(),
                path=f"{doc_id}.blocks[{block_index}].text",
                doc_id=doc_id,
            )

    def _observe(
        self,
        observations: dict[str, dict[str, Any]],
        *,
        label: str,
        value: Any,
        path: str,
        doc_id: str,
    ) -> None:
        normalized = self._normalize_label(label)
        if not normalized:
            return
        field_name = self.LABEL_ALIASES.get(normalized, self._field_id(normalized))
        item = observations[field_name]
        item["labels"].add(label.strip())
        if isinstance(value, str | int | float | bool) and str(value).strip():
            value_text = str(value).strip()
            if value_text not in item["values"]:
                item["values"].append(value_text)
        item["paths"].add(path)
        item["docs"].add(doc_id)

    def _candidate(
        self,
        field_name: str,
        data: dict[str, Any],
        sample_count: int,
    ) -> FieldCandidate:
        frequency = round(len(data["docs"]) / sample_count, 4)
        risk_flags = list(self.RISK_FLAGS.get(field_name, []))
        return FieldCandidate(
            field_name=field_name,
            source_labels=sorted(data["labels"]),
            value_examples=data["values"][:10],
            frequency=frequency,
            inferred_type=self._infer_type(field_name, data["labels"], data["values"]),
            evidence_paths=sorted(data["paths"]),
            risk_flags=risk_flags,
            confidence=round(min(0.99, 0.50 + frequency * 0.45), 4),
            review_required=bool(risk_flags),
        )

    def _infer_type(
        self,
        field_name: str,
        labels: set[str],
        values: list[str],
    ) -> str:
        text = "\n".join([field_name, *labels, *values])
        if field_name.endswith("_date") or self.DATE_PATTERN.search(text):
            return "date"
        if field_name.endswith("_amount") or self.AMOUNT_PATTERN.search(text):
            return "amount"
        if field_name.endswith("_id") or any("编号" in label for label in labels):
            return "identifier"
        return "string"

    @staticmethod
    def _normalize_label(label: str) -> str:
        normalized = unicodedata.normalize("NFKC", label)
        return re.sub(r"[\s:：\-_/（）()]+", "", normalized).strip()

    @staticmethod
    def _field_id(label: str) -> str:
        ascii_name = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        if ascii_name:
            return ascii_name
        digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:10]
        return f"field_{digest}"
