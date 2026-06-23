import hashlib

from app.schemas.canonical import CanonicalModel
from app.schemas.chunks import Chunk, ChunkLabels, ChunksJSON

DEFAULT_CHUNK_SIZE = 500


class ChunkEngine:
    def chunk(
        self,
        canonical: CanonicalModel,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> ChunksJSON:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        chunks: list[Chunk] = []
        current_text_parts: list[str] = []
        current_source_blocks: list[str] = []
        current_title_path: list[str] = []
        order = 0

        for block in canonical.blocks:
            block_text = block.text or ""
            is_heading = block.type == "heading"

            if is_heading:
                if current_text_parts:
                    chunks.append(self._make_chunk(
                        canonical,
                        order,
                        current_text_parts,
                        current_source_blocks,
                        current_title_path,
                    ))
                    order += 1
                    current_text_parts = []
                    current_source_blocks = []
                level = block.level or 1
                while len(current_title_path) >= level:
                    current_title_path.pop()
                current_title_path.append(block_text)
                current_text_parts.append(block_text)
                current_source_blocks.extend(block.source_blocks)
            else:
                candidate_text = (
                    "\n".join(current_text_parts + [block_text])
                    if current_text_parts else block_text
                )
                if len(candidate_text) > chunk_size and current_text_parts:
                    chunks.append(self._make_chunk(
                        canonical,
                        order,
                        current_text_parts,
                        current_source_blocks,
                        current_title_path,
                    ))
                    order += 1
                    current_text_parts = []
                    current_source_blocks = []
                current_text_parts.append(block_text)
                current_source_blocks.extend(block.source_blocks)

        if current_text_parts:
            chunks.append(self._make_chunk(
                canonical,
                order,
                current_text_parts,
                current_source_blocks,
                current_title_path,
            ))

        chunks = self._split_oversized_chunks(canonical, chunks, chunk_size)

        return ChunksJSON(
            chunks_version="1.0",
            doc_id=canonical.doc_id,
            task_id=canonical.task_id,
            chunks=chunks,
        )

    def _make_chunk(
        self,
        canonical: CanonicalModel,
        order: int,
        text_parts: list[str],
        source_blocks: list[str],
        title_path: list[str],
    ) -> Chunk:
        text = "\n".join(text_parts)
        unique_blocks = list(dict.fromkeys(source_blocks))
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        summary = self._fallback_summary(text)
        keywords = self._fallback_keywords(text)
        return Chunk(
            chunk_id=f"chk_{canonical.task_id}_{order}",
            order=order,
            text=text,
            source_blocks=unique_blocks,
            title_path=list(title_path),
            labels=self._fallback_labels(text, title_path, unique_blocks),
            summary=summary,
            keywords=keywords,
            text_hash=f"sha256:{text_hash}",
        )

    def _split_oversized_chunks(
        self,
        canonical: CanonicalModel,
        chunks: list[Chunk],
        chunk_size: int,
    ) -> list[Chunk]:
        normalized: list[Chunk] = []
        for chunk in chunks:
            text_parts = [
                chunk.text[offset : offset + chunk_size]
                for offset in range(0, len(chunk.text), chunk_size)
            ] or [""]
            for text in text_parts:
                normalized.append(
                    self._make_chunk(
                        canonical,
                        len(normalized),
                        [text],
                        chunk.source_blocks,
                        chunk.title_path,
                    )
                )
        return normalized

    @staticmethod
    def _fallback_summary(text: str) -> str:
        normalized = text.replace("\n", " ").strip()
        sentences = normalized.replace("。", ".").split(".")
        first = sentences[0].strip() if sentences else ""
        if first and normalized.endswith(("。", ".")):
            first += "。"
        return first[:200] if first else ""

    @staticmethod
    def _fallback_keywords(text: str) -> list[str]:
        words: list[str] = []
        punctuation = ",.;:\"'()[]{}，。、；：“”‘’（）《》"
        for segment in text.replace("\n", " ").split():
            clean = segment.strip(punctuation)
            if len(clean) >= 2:
                words.append(clean)
        seen: set[str] = set()
        unique: list[str] = []
        for word in words:
            if word not in seen:
                seen.add(word)
                unique.append(word)
        return unique[:5]

    @staticmethod
    def _fallback_labels(
        text: str,
        title_path: list[str],
        source_blocks: list[str],
    ) -> ChunkLabels:
        lowered = " ".join([*title_path, text]).lower()
        content_tags: list[str] = []
        if "policy" in lowered or "notice" in lowered or "政策" in lowered:
            content_tags.append("policy")
        if "|" in text:
            content_tags.append("table")
        if not content_tags:
            content_tags.append("general")
        return ChunkLabels(
            content_tags=list(dict.fromkeys(content_tags)),
            management_tags=["heading_context" if title_path else "body"],
            quality_tags=["linked" if source_blocks else "unlinked"],
        )
