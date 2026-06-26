import hashlib
from typing import Any

from app.schemas.canonical import CanonicalAsset, CanonicalBlock, CanonicalField, CanonicalModel
from app.schemas.mapping_template import MappingTemplate
from app.schemas.reports import MappingReport
from app.schemas.target_schema import TargetSchema
from app.schemas.uir import UIRBlock, UIRDocument
from app.services.transform_service import TransformResult


class CanonicalService:
    def build_canonical(
        self,
        task_id: str,
        uir: UIRDocument,
        schema: TargetSchema,
        template: MappingTemplate,
        transform_result: TransformResult,
        mapping_report: MappingReport,
        execution_snapshot: dict[str, Any],
    ) -> CanonicalModel:
        mappings_by_target = {
            mapping["target_field_id"]: mapping
            for mapping in mapping_report.mappings
        }
        fields = {}
        for field in schema.fields:
            if field.field_id not in transform_result.data:
                continue
            mapping = mappings_by_target.get(field.field_id, {})
            fields[field.field_id] = CanonicalField(
                value=transform_result.data[field.field_id],
                type=field.type,
                source_candidates=[mapping.get("candidate_id", "")] if mapping else [],
                source_blocks=mapping.get("source_blocks", []),
            )

        return CanonicalModel(
            canonical_version="1.0",
            task_id=task_id,
            doc_id=uir.doc_id,
            schema_id=schema.schema_id,
            doc_meta={
                "metadata": uir.metadata,
                "template_id": template.template_id,
                "mapping_summary": mapping_report.summary,
                "transform_summary": transform_result.report["summary"],
                "execution_snapshot": execution_snapshot,
            },
            fields=fields,
            blocks=[self._canonical_block(block) for block in uir.blocks],
            assets=[
                CanonicalAsset(
                    asset_id=asset.asset_id,
                    type=asset.type,
                    path=asset.path,
                    source_block_id=asset.source_block_id,
                )
                for asset in uir.assets
            ],
        )

    def _canonical_block(self, block: UIRBlock) -> CanonicalBlock:
        text = self._block_text(block)
        return CanonicalBlock(
            block_id=block.block_id,
            type=block.type,
            level=block.level,
            text=text,
            source_blocks=[block.block_id],
            source_anchor=block.source_anchor.model_dump(mode="json")
            if block.source_anchor
            else None,
            text_hash="sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

    @staticmethod
    def _block_text(block: UIRBlock) -> str:
        if block.text:
            return block.text
        if block.type == "list":
            items = block.attributes.get("items", [])
            if isinstance(items, list):
                return "\n".join(str(item) for item in items)
        if block.type == "table":
            rows = block.attributes.get("rows", [])
            if isinstance(rows, list):
                return "\n".join(
                    f"{row.get('field', '')}: {row.get('value', '')}"
                    for row in rows
                    if isinstance(row, dict)
                )
        return ""
