import re
from typing import Any

from app.schemas.mapping import FieldCandidate
from app.schemas.uir import UIRDocument
from app.utils.ids import new_id

LABEL_VALUE_RE = re.compile(r"(?P<label>[\w\u4e00-\u9fff]{2,20})[:：]\s*(?P<value>[^。\n]+)")


class FieldCandidateEngine:
    def extract(
        self,
        task_id: str,
        uir: UIRDocument,
        include_metadata: bool = True,
        include_blocks: bool = True,
        include_tables: bool = True,
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        if include_metadata:
            for key, value in uir.metadata.items():
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        doc_id=uir.doc_id,
                        source_path=f"metadata.{key}",
                        source_name=key,
                        value=value,
                        source_blocks=[],
                        evidence=["metadata field"],
                    )
                )

        if include_blocks:
            for block in uir.blocks:
                for key, value in block.attributes.items():
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            doc_id=uir.doc_id,
                            source_path=f"blocks.{block.block_id}.attributes.{key}",
                            source_name=key,
                            value=value,
                            source_blocks=[block.block_id],
                            evidence=["block attribute"],
                        )
                    )

                if block.type == "heading" and block.level == 1 and block.text:
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            doc_id=uir.doc_id,
                            source_path=f"blocks.{block.block_id}.text",
                            source_name="heading_title",
                            display_name="heading title",
                            value=block.text,
                            source_blocks=[block.block_id],
                            evidence=["level 1 heading"],
                        )
                    )

                if block.text:
                    for match in LABEL_VALUE_RE.finditer(block.text):
                        label = match.group("label")
                        value = match.group("value").strip()
                        candidates.append(
                            self._candidate(
                                task_id=task_id,
                                doc_id=uir.doc_id,
                                source_path=f"blocks.{block.block_id}.text.{label}",
                                source_name=label,
                                value=value,
                                source_blocks=[block.block_id],
                                evidence=["label-value text"],
                            )
                        )

                if include_tables and block.type == "table":
                    for column in self._table_columns(block.attributes):
                        candidates.append(
                            self._candidate(
                                task_id=task_id,
                                doc_id=uir.doc_id,
                                source_path=f"blocks.{block.block_id}.table.{column}",
                                source_name=column,
                                value=None,
                                source_blocks=[block.block_id],
                                evidence=["table column"],
                            )
                        )

        return self._deduplicate(candidates)

    def _candidate(
        self,
        task_id: str,
        doc_id: str,
        source_path: str,
        source_name: str,
        value: Any,
        source_blocks: list[str],
        evidence: list[str],
        display_name: str | None = None,
    ) -> FieldCandidate:
        return FieldCandidate(
            candidate_id=new_id("cand"),
            task_id=task_id,
            doc_id=doc_id,
            source_path=source_path,
            source_name=source_name,
            display_name=display_name or source_name,
            value_sample=value,
            inferred_type=self._infer_type(value),
            source_blocks=source_blocks,
            confidence=0.95,
            evidence=evidence,
        )

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            if re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}", value):
                return "date"
            return "string"
        return "string"

    @staticmethod
    def _table_columns(attributes: dict[str, Any]) -> list[str]:
        columns = attributes.get("columns") or attributes.get("table_columns")
        if isinstance(columns, list):
            return [str(column) for column in columns]
        return []

    @staticmethod
    def _deduplicate(candidates: list[FieldCandidate]) -> list[FieldCandidate]:
        seen: set[tuple[str, str]] = set()
        unique: list[FieldCandidate] = []
        for candidate in candidates:
            key = (candidate.source_path, str(candidate.value_sample))
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique
