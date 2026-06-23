from app.schemas.canonical import CanonicalModel
from app.schemas.content import (
    ContentAsset,
    ContentBlock,
    ContentJSON,
    ContentMetadata,
    ContentSchemaRef,
)


class JSONRenderer:
    def render(
        self,
        canonical: CanonicalModel,
        schema_version: str = "1.0.0",
    ) -> ContentJSON:
        data = {
            field_id: field.value
            for field_id, field in canonical.fields.items()
            if field.value is not None
        }
        metadata = ContentMetadata(
            source_name=canonical.doc_meta.get("source_name"),
            document_summary=self._summary_from_fields(canonical),
            keywords=self._keywords_from_fields(canonical),
            content_tags=self._content_tags(canonical),
            management_tags=self._management_tags(canonical),
            quality_tags=self._quality_tags(canonical),
            upstream_entities=self._upstream_entities(canonical),
        )
        blocks = [
            ContentBlock(
                block_id=b.block_id,
                type=b.type,
                level=b.level,
                text=b.text,
                source_blocks=b.source_blocks,
                text_hash=b.text_hash,
            )
            for b in canonical.blocks
        ]
        assets = [
            ContentAsset(
                asset_id=a.asset_id,
                type=a.type,
                path=a.path,
                source_block_id=a.source_block_id,
            )
            for a in canonical.assets
        ]
        return ContentJSON(
            content_version="1.1",
            doc_id=canonical.doc_id,
            task_id=canonical.task_id,
            schema_ref=ContentSchemaRef(
                schema_id=canonical.schema_id,
                version=schema_version,
            ),
            metadata=metadata,
            data=data,
            blocks=blocks,
            assets=assets,
        )

    @staticmethod
    def _summary_from_fields(canonical: CanonicalModel) -> str | None:
        for key in ("summary", "摘要", "document_summary"):
            field = canonical.fields.get(key)
            if field and field.value:
                return str(field.value)
        for block in canonical.blocks:
            if block.type == "paragraph" and block.text.strip():
                return block.text.strip()[:200]
        for block in canonical.blocks:
            if block.text.strip():
                return block.text.strip()[:200]
        return None

    @staticmethod
    def _keywords_from_fields(canonical: CanonicalModel) -> list[str]:
        for key in ("keywords", "关键词"):
            field = canonical.fields.get(key)
            if field and field.value:
                if isinstance(field.value, list):
                    return [str(v) for v in field.value]
                return [str(field.value)]
        fallback: list[str] = []
        for key in ("title", "publish_org", "author", "doc_type"):
            field = canonical.fields.get(key)
            if field and field.value:
                value = str(field.value)
                if value not in fallback:
                    fallback.append(value)
        return fallback[:5]

    @staticmethod
    def _content_tags(canonical: CanonicalModel) -> list[str]:
        tags: list[str] = []
        doc_type = canonical.fields.get("doc_type")
        if doc_type and doc_type.value:
            tags.append(str(doc_type.value))
        combined = " ".join(
            str(field.value)
            for field in canonical.fields.values()
            if field.value is not None
        ).lower()
        if "policy" in combined or "notice" in combined or "政策" in combined:
            tags.append("policy")
        if any(block.type == "table" for block in canonical.blocks):
            tags.append("table")
        if not tags:
            tags.append("general")
        return list(dict.fromkeys(tags))[:6]

    @staticmethod
    def _management_tags(canonical: CanonicalModel) -> list[str]:
        tags = [f"schema:{canonical.schema_id}"]
        tags.append("has_blocks" if canonical.blocks else "no_blocks")
        if canonical.assets:
            tags.append("has_assets")
        return tags

    @staticmethod
    def _quality_tags(canonical: CanonicalModel) -> list[str]:
        linked_blocks = all(block.source_blocks for block in canonical.blocks)
        return [
            "source_linked" if linked_blocks else "source_link_missing",
            "has_summary" if JSONRenderer._summary_from_fields(canonical) else "summary_fallback",
        ]

    @staticmethod
    def _upstream_entities(canonical: CanonicalModel) -> list[str]:
        entities: list[str] = []
        for field_id in ("publish_org", "author", "owner"):
            field = canonical.fields.get(field_id)
            if field and field.value:
                entities.append(f"{field_id}:{field.value}")
        source_name = canonical.doc_meta.get("source_name")
        if source_name:
            entities.append(f"source_name:{source_name}")
        return list(dict.fromkeys(str(entity) for entity in entities))
