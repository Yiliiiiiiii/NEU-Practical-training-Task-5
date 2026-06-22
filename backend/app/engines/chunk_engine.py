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
                        canonical, order, current_text_parts,
                        current_source_blocks, current_title_path,
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
                        canonical, order, current_text_parts,
                        current_source_blocks, current_title_path,
                    ))
                    order += 1
                    current_text_parts = []
                    current_source_blocks = []
                current_text_parts.append(block_text)
                current_source_blocks.extend(block.source_blocks)

        if current_text_parts:
            chunks.append(self._make_chunk(
                canonical, order, current_text_parts,
                current_source_blocks, current_title_path,
            ))

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
            labels=ChunkLabels(),
            summary=summary,
            keywords=keywords,
            text_hash=f"sha256:{text_hash}",
        )

    @staticmethod
    def _fallback_summary(text: str) -> str:
        sentences = text.replace("\n", " ").split("。")
        first = sentences[0].strip() if sentences else ""
        if first and not first.endswith("。"):
            first += "。"
        return first[:200] if first else ""

    @staticmethod
    def _fallback_keywords(text: str) -> list[str]:
        words: list[str] = []
        punctuation = "，。、；：\u201c\u201d\u2018\u2019（）《》"
        for segment in text.replace("\n", " ").split():
            clean = segment.strip(punctuation)
            if len(clean) >= 2:
                words.append(clean)
        seen: set[str] = set()
        unique: list[str] = []
        for w in words:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return unique[:5]
