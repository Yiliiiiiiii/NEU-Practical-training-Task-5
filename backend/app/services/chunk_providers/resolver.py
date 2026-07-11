from __future__ import annotations

import re
from typing import Any

from app.config import Settings
from app.schemas.canonical import CanonicalModel
from app.schemas.chunk_provider import (
    ChunkProviderBlock,
    ChunkProviderRequest,
    ChunkProviderResponse,
    ChunkProviderTrace,
)
from app.schemas.content_organization import ContentOrganizationOptions
from app.services.chunk_providers.base import (
    ChunkProvider,
    ChunkProviderError,
    ChunkProviderInvocation,
    ChunkProviderResult,
)
from app.services.chunk_providers.internal import InternalDeterministicChunkProvider
from app.services.chunk_providers.topic11_http import Topic11HttpChunkProvider


class ChunkProviderResolver:
    def __init__(
        self,
        *,
        settings: Settings,
        internal_provider: ChunkProvider | None = None,
        external_provider: ChunkProvider | None = None,
    ) -> None:
        self.settings = settings
        self.internal_provider = internal_provider or InternalDeterministicChunkProvider()
        self.external_provider = external_provider or Topic11HttpChunkProvider(settings)

    def resolve(
        self,
        *,
        canonical: CanonicalModel,
        options: ContentOrganizationOptions | None,
        legacy_chunks: list[dict[str, Any]],
    ) -> ChunkProviderResult:
        if options is None:
            return ChunkProviderResult(
                chunks=legacy_chunks,
                trace=ChunkProviderTrace(
                    requested_provider="internal",
                    used_provider="internal",
                    provider_version="legacy-render-1.0",
                    validation_passed=True,
                ),
            )

        self._validate_exclusions(canonical=canonical, options=options)
        request = self.build_request(canonical, options)
        if options.provider == "internal":
            invocation = self.internal_provider.provide(request)
            self._validate(invocation.response, canonical=canonical, options=options)
            return self._result(
                invocation,
                requested_provider="internal",
                external_requested=False,
            )

        try:
            invocation = self.external_provider.provide(request)
            self._validate(invocation.response, canonical=canonical, options=options)
            return self._result(
                invocation,
                requested_provider="topic11",
                external_requested=True,
            )
        except ChunkProviderError as exc:
            reason = exc.code
        except Exception:
            reason = "topic11_provider_error"

        if options.strict_provider or not options.fallback_to_internal:
            raise ChunkProviderError(reason)
        internal = self.internal_provider.provide(request)
        try:
            self._validate(internal.response, canonical=canonical, options=options)
        except ChunkProviderError:
            raise ChunkProviderError("internal_provider_invalid") from None
        return self._result(
            internal,
            requested_provider="topic11",
            external_requested=True,
            fallback_reason=reason,
        )

    @staticmethod
    def build_request(
        canonical: CanonicalModel,
        options: ContentOrganizationOptions,
    ) -> ChunkProviderRequest:
        return ChunkProviderRequest(
            task_id=canonical.task_id,
            doc_id=canonical.doc_id,
            schema_id=canonical.schema_id,
            blocks=[
                ChunkProviderBlock(
                    block_id=block.block_id,
                    type=block.type,
                    text=block.text,
                    source_blocks=block.source_blocks,
                    protected=(
                        (options.protect_tables and block.type == "table")
                        or (options.protect_lists and block.type == "list")
                        or (
                            options.protect_code_blocks
                            and block.type in {"code", "code_block"}
                        )
                    ),
                    level=block.level,
                    source_anchor=block.source_anchor,
                )
                for block in canonical.blocks
            ],
            entities=(
                canonical.doc_meta.get("entities", [])
                if isinstance(canonical.doc_meta.get("entities", []), list)
                else []
            ),
            document_metadata=(
                canonical.doc_meta.get("document_metadata", {})
                if isinstance(canonical.doc_meta.get("document_metadata", {}), dict)
                else {}
            ),
            chunk_config=options.model_dump(mode="json"),
        )

    @classmethod
    def _validate_exclusions(
        cls,
        *,
        canonical: CanonicalModel,
        options: ContentOrganizationOptions,
    ) -> None:
        blocks = {block.block_id: block for block in canonical.blocks}
        for exclusion in options.block_exclusions:
            block = blocks.get(exclusion.block_id)
            if block is None:
                raise ChunkProviderError("topic11_exclusion_block_unknown")
            if cls._is_protected(block.type, options):
                raise ChunkProviderError("topic11_protected_block_exclusion")

    @staticmethod
    def _is_protected(
        block_type: str, options: ContentOrganizationOptions
    ) -> bool:
        return (
            (options.protect_tables and block_type == "table")
            or (options.protect_lists and block_type == "list")
            or (
                options.protect_code_blocks
                and block_type in {"code", "code_block"}
            )
        )

    @classmethod
    def _validate(
        cls,
        response: ChunkProviderResponse,
        *,
        canonical: CanonicalModel,
        options: ContentOrganizationOptions,
    ) -> None:
        if not response.chunks:
            raise ChunkProviderError("topic11_chunks_empty")
        blocks = {block.block_id: block for block in canonical.blocks}
        known_entity_ids = {
            str(entity["normalized_id"])
            for entity in canonical.doc_meta.get("entities", [])
            if isinstance(entity, dict) and entity.get("normalized_id")
        }
        chunk_ids = {chunk.chunk_id for chunk in response.chunks}
        referenced_blocks: set[str] = set()
        for chunk in response.chunks:
            if not chunk.text.strip():
                raise ChunkProviderError("topic11_chunk_text_empty")
            unknown_blocks = set(chunk.source_block_ids) - blocks.keys()
            if unknown_blocks:
                raise ChunkProviderError("topic11_unknown_source_block")
            referenced_blocks.update(chunk.source_block_ids)
            source_text = "\n\n".join(
                blocks[block_id].text for block_id in chunk.source_block_ids
            )
            if cls._normalize(chunk.text) not in cls._normalize(source_text):
                raise ChunkProviderError("topic11_chunk_text_not_derivable")
            if set(chunk.entity_ids) - known_entity_ids:
                raise ChunkProviderError("topic11_unknown_entity_id")
            if chunk.parent_chunk_id and chunk.parent_chunk_id not in chunk_ids:
                raise ChunkProviderError("topic11_parent_chunk_missing")

        protected_blocks = {
            block.block_id
            for block in canonical.blocks
            if cls._is_protected(block.type, options)
        }
        if protected_blocks - referenced_blocks:
            raise ChunkProviderError("topic11_protected_block_missing")
        nonempty_blocks = {
            block.block_id for block in canonical.blocks if block.text.strip()
        }
        protected_exclusions = {
            exclusion.block_id
            for exclusion in options.block_exclusions
            if exclusion.block_id in protected_blocks
        }
        if protected_exclusions:
            raise ChunkProviderError("topic11_protected_block_exclusion")
        exclusions = {
            exclusion.block_id
            for exclusion in options.block_exclusions
            if exclusion.block_id in blocks and exclusion.block_id not in protected_blocks
        }
        if (nonempty_blocks - exclusions) - referenced_blocks:
            raise ChunkProviderError("topic11_canonical_block_missing")
        for block_id in protected_blocks:
            block_text = blocks[block_id].text
            if not any(
                (
                    chunk.source_block_ids == [block_id]
                    and chunk.text == block_text
                )
                or (
                    len(chunk.source_block_ids) > 1
                    and block_id in chunk.source_block_ids
                    and block_text in chunk.text
                )
                for chunk in response.chunks
            ):
                raise ChunkProviderError("topic11_protected_block_integrity")

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _result(
        invocation: ChunkProviderInvocation,
        *,
        requested_provider: str,
        external_requested: bool,
        fallback_reason: str | None = None,
    ) -> ChunkProviderResult:
        response = invocation.response
        used_provider = response.provider
        trace = ChunkProviderTrace(
            requested_provider=requested_provider,
            used_provider=used_provider,
            provider_version=response.provider_version,
            external_requested=external_requested,
            external_used=used_provider == "topic11",
            fallback_used=fallback_reason is not None,
            fallback_reason=fallback_reason,
            latency_ms=invocation.latency_ms,
            validation_passed=True,
        )
        return ChunkProviderResult(
            chunks=[chunk.model_dump(mode="json") for chunk in response.chunks],
            trace=trace,
        )
