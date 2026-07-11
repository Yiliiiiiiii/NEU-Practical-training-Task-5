from __future__ import annotations

from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.chunk_provider import (
    ChunkProviderRequest,
    ChunkProviderResponse,
)
from app.schemas.content_organization import ContentOrganizationOptions
from app.services.chunk_organizer_service import ChunkOrganizerService
from app.services.chunk_providers.base import ChunkProviderInvocation


class InternalDeterministicChunkProvider:
    provider_version = "internal-1.0"

    def provide(self, request: ChunkProviderRequest) -> ChunkProviderInvocation:
        options = ContentOrganizationOptions.model_validate(request.chunk_config)
        canonical = CanonicalModel(
            canonical_version="1.0",
            task_id=request.task_id,
            doc_id=request.doc_id,
            schema_id=request.schema_id,
            doc_meta={
                "document_metadata": request.document_metadata,
                "entities": request.entities,
            },
            blocks=[
                CanonicalBlock(
                    block_id=block.block_id,
                    type=block.type,
                    level=block.level,
                    text=block.text,
                    source_blocks=block.source_blocks or [block.block_id],
                    source_anchor=block.source_anchor,
                )
                for block in request.blocks
            ],
        )
        chunks = ChunkOrganizerService().build_strategy_chunks(
            canonical_model=canonical,
            doc_id=request.doc_id,
            task_id=canonical.task_id,
            options=options,
        )
        response = ChunkProviderResponse.model_validate(
            {
                "contract_version": "1.0",
                "provider": "internal",
                "provider_version": self.provider_version,
                "chunks": chunks,
                "warnings": [],
                "trace": {"strategy": options.chunk_strategy},
            }
        )
        return ChunkProviderInvocation(response=response)
