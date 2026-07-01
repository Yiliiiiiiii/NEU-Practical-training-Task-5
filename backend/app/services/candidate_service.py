import re
from typing import Any

from app.schemas.mapping import FieldCandidate
from app.schemas.uir import UIRDocument


class CandidateService:
    CONTROL_METADATA_KEYS = {
        "domain",
        "expected_learning_fields",
        "expected_review_fields",
        "scenario",
    }

    def extract_candidates(self, task_id: str, uir: UIRDocument) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        seen_names: dict[str, int] = {}

        for key, value in uir.metadata.items():
            if key in self.CONTROL_METADATA_KEYS:
                continue
            candidates.append(
                self._candidate(
                    task_id=task_id,
                    uir=uir,
                    source_path=f"$.metadata.{key}",
                    source_name=key,
                    value=value,
                    source_blocks=[],
                    source_kind="metadata",
                    seen_names=seen_names,
                )
            )

        for block in uir.blocks:
            if block.type == "table":
                rows = block.attributes.get("rows", [])
                if not isinstance(rows, list):
                    continue
                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    source_name = row.get("field")
                    if not isinstance(source_name, str) or not source_name.strip():
                        continue
                    candidates.append(
                        self._candidate(
                            task_id=task_id,
                            uir=uir,
                            source_path=f"$.blocks.{block.block_id}.rows.{index}",
                            source_name=source_name.strip(),
                            value=row.get("value"),
                            source_blocks=[block.block_id],
                            source_kind="table",
                            seen_names=seen_names,
                        )
                    )
            elif block.attributes.get("field_name"):
                source_name = str(block.attributes["field_name"]).strip()
                if not source_name:
                    continue
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path=f"$.blocks.{block.block_id}.text",
                        source_name=source_name,
                        value=block.text,
                        source_blocks=[block.block_id],
                        source_kind="block",
                        seen_names=seen_names,
                    )
                )

        has_content = any(
            self.normalize_name(item.source_name) == "content" for item in candidates
        )
        has_named_text_block = any(item.source_path.endswith(".text") for item in candidates)
        if not has_content and not has_named_text_block:
            content_parts: list[str] = []
            content_blocks: list[str] = []
            for block in uir.blocks:
                block_text = self._block_text(block.text, block.attributes)
                if not block_text:
                    continue
                content_parts.append(block_text)
                content_blocks.append(block.block_id)
            if content_parts:
                candidates.append(
                    self._candidate(
                        task_id=task_id,
                        uir=uir,
                        source_path="blocks[*].text",
                        source_name="document text",
                        value="\n".join(content_parts),
                        source_blocks=content_blocks,
                        source_kind="aggregate_blocks",
                        seen_names=seen_names,
                    )
                )

        if uir.metadata.get("domain") == "meeting_doc":
            meeting_date = self._meeting_date_candidate(task_id, uir, seen_names)
            if meeting_date is not None:
                candidates.append(meeting_date)

        return candidates

    def _meeting_date_candidate(
        self,
        task_id: str,
        uir: UIRDocument,
        seen_names: dict[str, int],
    ) -> FieldCandidate | None:
        patterns = [
            re.compile(r"\d{4}\s*[年/-]\s*\d{1,2}\s*[月/-]\s*\d{1,2}\s*日?"),
            re.compile(r"[二〇○零一二三四五六七八九十]{4}\s*年\s*[一二三四五六七八九十]{1,3}\s*月\s*[一二三四五六七八九十]{1,3}\s*日"),
            re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日"),
        ]
        matches: list[tuple[int, int, str, str]] = []
        for index, block in enumerate(uir.blocks):
            text = block.text or ""
            if not text or "生成日期" in text:
                continue
            for pattern in patterns:
                match = pattern.search(text)
                if match is None:
                    continue
                score = 3 if "主持召开" in text else 2 if "日期" in text else 1
                matches.append((score, -index, match.group(0), block.block_id))
                break
        if not matches:
            return None
        _score, _index, value, block_id = max(matches)
        return self._candidate(
            task_id=task_id,
            uir=uir,
            source_path=f"$.blocks.{block_id}.text",
            source_name="meeting date",
            value=value,
            source_blocks=[block_id],
            source_kind="derived_meeting_date",
            seen_names=seen_names,
        )

    @staticmethod
    def _block_text(text: str | None, attributes: dict[str, Any]) -> str:
        if text and text.strip():
            return text.strip()
        rows = attributes.get("rows")
        if isinstance(rows, list):
            values = []
            for row in rows:
                if isinstance(row, dict):
                    values.append(
                        ": ".join(
                            str(value).strip()
                            for value in row.values()
                            if value is not None and str(value).strip()
                        )
                    )
            return "\n".join(value for value in values if value)
        items = attributes.get("items")
        if isinstance(items, list):
            return "\n".join(str(item).strip() for item in items if str(item).strip())
        return ""

    def _candidate(
        self,
        task_id: str,
        uir: UIRDocument,
        source_path: str,
        source_name: str,
        value: Any,
        source_blocks: list[str],
        source_kind: str,
        seen_names: dict[str, int],
    ) -> FieldCandidate:
        normalized_name = self.normalize_name(source_name)
        seen_names[normalized_name] = seen_names.get(normalized_name, 0) + 1
        suffix = seen_names[normalized_name]
        return FieldCandidate(
            candidate_id=f"cand_{task_id}_{self.sanitize(source_name)}_{suffix}",
            task_id=task_id,
            doc_id=uir.doc_id,
            source_path=source_path,
            source_name=source_name,
            display_name=source_name,
            value_sample=value,
            inferred_type=self.infer_type(value),
            source_blocks=source_blocks,
            confidence=0.8,
            evidence=[f"extracted from {source_kind}"],
        )

    @staticmethod
    def infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int | float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, str):
            stripped = value.strip()
            if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", stripped):
                return "date"
            if re.fullmatch(r"[¥￥]?\s*\d[\d,]*(?:\.\d+)?\s*(?:元)?", stripped):
                return "number"
            return "string"
        return "string"

    @staticmethod
    def normalize_name(value: str) -> str:
        return re.sub(r"[\s_\-]+", "", value.strip().lower())

    @staticmethod
    def sanitize(value: str) -> str:
        return re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", value).strip("_") or "source"
