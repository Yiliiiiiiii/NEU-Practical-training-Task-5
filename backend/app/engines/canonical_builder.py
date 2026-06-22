import hashlib

from app.schemas.canonical import CanonicalAsset, CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.uir import UIRDocument


class CanonicalBuilder:
    def build(
        self,
        task_id: str,
        doc_id: str,
        schema_id: str,
        fields: dict[str, CanonicalField],
        uir: UIRDocument,
    ) -> CanonicalModel:
        blocks = self._build_blocks(uir)
        assets = self._build_assets(uir)
        doc_meta = dict(uir.metadata)
        if uir.source and uir.source.source_name:
            doc_meta.setdefault("source_name", uir.source.source_name)
        return CanonicalModel(
            canonical_version="1.0",
            task_id=task_id,
            doc_id=doc_id,
            schema_id=schema_id,
            doc_meta=doc_meta,
            fields=fields,
            blocks=blocks,
            assets=assets,
        )

    def _build_blocks(self, uir: UIRDocument) -> list[CanonicalBlock]:
        blocks: list[CanonicalBlock] = []
        for block in uir.blocks:
            text = block.text or ""
            blocks.append(
                CanonicalBlock(
                    block_id=block.block_id,
                    type=block.type,
                    level=block.level,
                    text=text,
                    source_blocks=[block.block_id],
                    text_hash=f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}",
                )
            )
        return blocks

    def _build_assets(self, uir: UIRDocument) -> list[CanonicalAsset]:
        return [
            CanonicalAsset(
                asset_id=asset.asset_id,
                type=asset.type,
                path=asset.path,
                source_block_id=asset.source_block_id,
            )
            for asset in uir.assets
        ]
