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
        return None

    @staticmethod
    def _keywords_from_fields(canonical: CanonicalModel) -> list[str]:
        for key in ("keywords", "关键词"):
            field = canonical.fields.get(key)
            if field and field.value:
                if isinstance(field.value, list):
                    return [str(v) for v in field.value]
                return [str(field.value)]
        return []
