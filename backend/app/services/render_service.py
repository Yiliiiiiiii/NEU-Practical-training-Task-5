import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.schemas.canonical import CanonicalBlock, CanonicalModel

_INTERNAL_METADATA_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "credentials",
    "doc_id",
    "duration_ms",
    "elapsed_ms",
    "field_traces",
    "mapping_summary",
    "package_id",
    "password",
    "refresh_token",
    "report_paths",
    "runtime_duration_ms",
    "schema_id",
    "secret",
    "task_id",
    "transform_summary",
}
_OPERATIONAL_METADATA_SUFFIXES = (
    "_duration",
    "_duration_ms",
    "_report",
    "_reports",
    "_report_path",
    "_report_paths",
    "_snapshot",
    "_snapshots",
    "_trace",
)
_CREDENTIAL_METADATA_SUFFIXES = (
    "_access_token",
    "_api_key",
    "_authorization",
    "_credential",
    "_credentials",
    "_password",
    "_refresh_token",
    "_secret",
    "_token",
)


def _is_internal_metadata_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.casefold()
    return normalized in _INTERNAL_METADATA_KEYS or normalized.endswith(
        _OPERATIONAL_METADATA_SUFFIXES + _CREDENTIAL_METADATA_SUFFIXES
    )


@dataclass(frozen=True)
class RenderedArtifacts:
    structured_json: dict[str, Any]
    markdown: str
    chunks: list[dict[str, Any]]


class RenderService:
    def render(self, canonical: CanonicalModel, chunk_size: int = 1200) -> RenderedArtifacts:
        source_metadata = canonical.doc_meta.get(
            "source_metadata", canonical.doc_meta.get("metadata", {})
        )
        source_metadata = source_metadata if isinstance(source_metadata, dict) else {}
        document_metadata = canonical.doc_meta.get("document_metadata", {})
        document_metadata = (
            document_metadata if isinstance(document_metadata, dict) else {}
        )
        metadata_template = canonical.doc_meta.get("metadata_template")
        document_summary = canonical.doc_meta.get("document_summary")
        content_metadata_template = (
            {
                key: metadata_template[key]
                for key in ("template_id", "version")
                if key in metadata_template
            }
            if isinstance(metadata_template, dict)
            else {}
        )
        content_document_summary = (
            document_summary if isinstance(document_summary, dict) else {}
        )
        source_metadata = self._sanitize_metadata_value(source_metadata)
        document_metadata = self._sanitize_metadata_value(document_metadata)
        structured = {
            "source_metadata": source_metadata,
            "document_metadata": document_metadata,
            "metadata_template": content_metadata_template,
            "document_summary": self._sanitize_metadata_value(
                content_document_summary
            ),
            "data": {
                field_id: field.value for field_id, field in canonical.fields.items()
            },
            "blocks": [self._content_block(block) for block in canonical.blocks],
            "assets": [asset.model_dump(mode="json") for asset in canonical.assets],
            # Deprecated Package 1.1 alias. New consumers should use the two
            # explicit metadata fields above.
            "metadata": {**source_metadata, **document_metadata},
        }
        return RenderedArtifacts(
            structured_json=structured,
            markdown=self._markdown(canonical),
            chunks=self._chunks(canonical, chunk_size=chunk_size),
        )

    @classmethod
    def _sanitize_metadata_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: cls._sanitize_metadata_value(child)
                for key, child in value.items()
                if not _is_internal_metadata_key(key)
            }
        if isinstance(value, list):
            return [cls._sanitize_metadata_value(child) for child in value]
        return value

    @classmethod
    def _content_block(cls, block: CanonicalBlock) -> dict[str, Any]:
        payload = block.model_dump(mode="json")
        source_anchor = payload.get("source_anchor")
        if isinstance(source_anchor, dict):
            payload["source_anchor"] = cls._sanitize_metadata_value(source_anchor)
        return payload

    def _markdown(self, canonical: CanonicalModel) -> str:
        lines = [
            (
                '<!-- topic5:document:start '
                f'doc_id="{self._marker_value(canonical.doc_id)}" '
                f'schema_id="{self._marker_value(canonical.schema_id)}" -->'
            )
        ]
        document_summary = canonical.doc_meta.get("document_summary")
        summary_text = (
            str(document_summary.get("text") or "")
            if isinstance(document_summary, dict)
            else ""
        )
        lines.extend(
            [
                "## Document Summary",
                '<!-- topic5:summary:start -->',
                self._escape_protocol_text(summary_text),
                '<!-- topic5:summary:end -->',
                "## Structured Data",
                '<!-- topic5:structured-data:start -->',
                "```json",
                json.dumps(
                    {
                        "data": {
                            field_id: field.value
                            for field_id, field in canonical.fields.items()
                        },
                        "document_metadata": canonical.doc_meta.get(
                            "document_metadata", {}
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                "```",
                '<!-- topic5:structured-data:end -->',
                "## Content",
            ]
        )
        for block in canonical.blocks:
            text = block.text
            block_hash = self._text_hash(text)
            lines.append(
                '<!-- topic5:block:start '
                f'id="{self._marker_value(block.block_id)}" hash="{block_hash}" -->'
            )
            lines.extend(self.markdown_block_content(block))
            lines.append(
                f'<!-- topic5:block:end id="{self._marker_value(block.block_id)}" -->'
            )
        lines.append("<!-- topic5:document:end -->")
        return "\n".join(lines) + "\n"

    @classmethod
    def markdown_block_content(cls, block: CanonicalBlock) -> list[str]:
        text = block.text
        if block.type == "heading":
            level = min(max(block.level or 1, 1), 6)
            return [f"{'#' * level} {cls._escape_protocol_text(text.strip())}"]
        if block.type == "list":
            return [f"- {cls._escape_protocol_text(item)}" for item in text.splitlines()]
        if block.type == "table":
            return cls._markdown_table(block)
        if block.type == "code":
            fence = "````" if "```" in text else "```"
            return [fence, cls._escape_protocol_text(text), fence]
        return [cls._escape_protocol_text(text)]

    @staticmethod
    def _markdown_table(block: CanonicalBlock) -> list[str]:
        rows = []
        for line in block.text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                rows.append((key.strip(), value.strip()))
        if not rows:
            return [RenderService._escape_protocol_text(block.text)]
        output = ["| Field | Value |", "| --- | --- |"]
        output.extend(
            f"| {RenderService._table_cell(key)} | {RenderService._table_cell(value)} |"
            for key, value in rows
        )
        return output

    @staticmethod
    def _text_hash(text: str) -> str:
        return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _marker_value(value: str) -> str:
        return value.replace("&", "&amp;").replace('"', "&quot;")

    @staticmethod
    def _escape_protocol_text(text: str) -> str:
        return text.replace("<!-- topic5:", "&lt;!-- topic5:")

    @staticmethod
    def _table_cell(text: str) -> str:
        return (
            RenderService._escape_protocol_text(text)
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\r\n", "<br>")
            .replace("\r", "<br>")
            .replace("\n", "<br>")
        )

    def _chunks(self, canonical: CanonicalModel, chunk_size: int) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        title_path: list[str] = []
        for block in canonical.blocks:
            text = block.text.strip()
            if not text:
                continue
            if block.type == "heading":
                level = block.level or 1
                title_path = title_path[: level - 1] + [text]
            for index, piece in enumerate(self._split_text(text, chunk_size), start=1):
                chunks.append(
                    {
                        "chunk_id": f"chunk_{canonical.doc_id}_{block.block_id}_{index}",
                        "text": piece,
                        "source_block_ids": block.source_blocks,
                        "title_path": title_path,
                    }
                )
        return chunks

    @staticmethod
    def _split_text(text: str, chunk_size: int) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]
