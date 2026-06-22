from app.schemas.canonical import CanonicalModel


class MarkdownRenderer:
    def render(self, canonical: CanonicalModel) -> str:
        parts: list[str] = []

        parts.append("---")
        parts.append(f"doc_id: {canonical.doc_id}")
        parts.append(f"task_id: {canonical.task_id}")
        parts.append(f"schema_id: {canonical.schema_id}")
        title = self._pick_title(canonical)
        if title:
            parts.append(f"title: {title}")
        parts.append("---")
        parts.append("")

        if title:
            parts.append(f"# {title}")
            parts.append("")

        for block in canonical.blocks:
            source_blocks_str = ", ".join(block.source_blocks)
            parts.append(
                f"<!-- block_id: {block.block_id} | "
                f"source_blocks: {source_blocks_str} -->"
            )
            level = block.level or 1
            if block.type == "heading":
                prefix = "#" * min(level, 6)
                parts.append(f"{prefix} {block.text}")
            elif block.type == "table":
                parts.append(self._render_table(block.text))
            else:
                parts.append(block.text if block.text else "")
            parts.append("")

        for asset in canonical.assets:
            parts.append(
                f"<!-- asset_id: {asset.asset_id} | "
                f"source_block_id: {asset.source_block_id or ''} -->"
            )
            parts.append(f"![{asset.asset_id}]({asset.path})")
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def _pick_title(canonical: CanonicalModel) -> str | None:
        for key in ("title", "标题", "政策名称", "文档标题"):
            field = canonical.fields.get(key)
            if field and field.value:
                return str(field.value)
        if canonical.blocks:
            first = canonical.blocks[0]
            if first.type == "heading" and first.text:
                return first.text
        return None

    @staticmethod
    def _render_table(text: str) -> str:
        return text if text else ""
