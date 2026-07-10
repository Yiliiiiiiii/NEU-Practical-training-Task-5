from dataclasses import dataclass
from typing import Any

from app.schemas.canonical import CanonicalBlock, CanonicalModel


@dataclass(frozen=True)
class RenderedArtifacts:
    structured_json: dict[str, Any]
    markdown: str
    chunks: list[dict[str, Any]]


class RenderService:
    def render(self, canonical: CanonicalModel, chunk_size: int = 1200) -> RenderedArtifacts:
        source_metadata = canonical.doc_meta.get("metadata", {})
        source_metadata = source_metadata if isinstance(source_metadata, dict) else {}
        structured = {
            "task_id": canonical.task_id,
            "doc_id": canonical.doc_id,
            "schema_id": canonical.schema_id,
            "data": {
                field_id: field.value
                for field_id, field in canonical.fields.items()
            },
            "metadata": {**source_metadata, **canonical.doc_meta},
            "blocks": [block.model_dump(mode="json") for block in canonical.blocks],
            "assets": [asset.model_dump(mode="json") for asset in canonical.assets],
            "execution_snapshot": canonical.doc_meta.get("execution_snapshot", {}),
        }
        return RenderedArtifacts(
            structured_json=structured,
            markdown=self._markdown(canonical),
            chunks=self._chunks(canonical, chunk_size=chunk_size),
        )

    def _markdown(self, canonical: CanonicalModel) -> str:
        lines: list[str] = []
        for block in canonical.blocks:
            text = block.text.strip()
            if not text:
                continue
            if block.type == "heading":
                level = min(max(block.level or 1, 1), 6)
                lines.append(f"{'#' * level} {text}")
            elif block.type == "list":
                for item in text.splitlines():
                    lines.append(f"- {item}")
            elif block.type == "table":
                lines.extend(self._markdown_table(block))
            else:
                lines.append(text)
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _markdown_table(block: CanonicalBlock) -> list[str]:
        rows = []
        for line in block.text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                rows.append((key.strip(), value.strip()))
        if not rows:
            return [block.text]
        output = ["| Field | Value |", "| --- | --- |"]
        output.extend(f"| {key} | {value} |" for key, value in rows)
        return output

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
