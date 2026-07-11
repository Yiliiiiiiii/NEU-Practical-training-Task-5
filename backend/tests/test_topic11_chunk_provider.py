from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.canonical import CanonicalBlock, CanonicalModel
from app.schemas.chunk_provider import ChunkProviderRequest, ChunkProviderResponse
from app.schemas.content_organization import ContentOrganizationOptions
from app.services.chunk_providers.base import (
    ChunkProviderError,
    ChunkProviderInvocation,
)
from app.services.chunk_providers.resolver import ChunkProviderResolver
from app.services.chunk_providers.topic11_http import Topic11HttpChunkProvider

ROOT = Path(__file__).resolve().parents[2]


def _canonical() -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task-provider",
        doc_id="doc-provider",
        schema_id="provider_doc",
        doc_meta={
            "document_metadata": {"language": "en-US"},
            "entities": [
                {
                    "mention": "OpenAI",
                    "canonical_name": "OpenAI",
                    "entity_type": "organization",
                    "normalized_id": "org:openai",
                    "link_status": "linked",
                    "confidence": 1.0,
                    "source_block_ids": ["b1"],
                    "source_agent": "topic7",
                    "evidence": {},
                }
            ],
        },
        blocks=[
            CanonicalBlock(
                block_id="b1",
                type="paragraph",
                text="OpenAI published the notice.",
                source_blocks=["b1"],
            ),
            CanonicalBlock(
                block_id="table1",
                type="table",
                text="Field: Value",
                source_blocks=["table1"],
            ),
        ],
    )


def _options(**overrides) -> ContentOrganizationOptions:
    payload = {
        "chunk_strategy": "source_block_aware",
        "target_tokens": 128,
        "min_tokens": 1,
        "max_tokens": 256,
        "overlap_tokens": 0,
        "provider": "topic11",
        "fallback_to_internal": True,
        "strict_provider": False,
        **overrides,
    }
    return ContentOrganizationOptions.model_validate(payload)


def _legacy_chunks() -> list[dict]:
    return [
        {
            "chunk_id": "legacy-b1",
            "text": "OpenAI published the notice.",
            "source_block_ids": ["b1"],
        },
        {
            "chunk_id": "legacy-table1",
            "text": "Field: Value",
            "source_block_ids": ["table1"],
        },
    ]


class FakeProvider:
    def __init__(self, response: ChunkProviderResponse | None = None, error: str | None = None):
        self.response = response
        self.error = error

    def provide(self, request):
        if self.error:
            raise ChunkProviderError(self.error)
        assert self.response is not None
        return ChunkProviderInvocation(response=self.response, latency_ms=7)


def _response(*chunks: dict) -> ChunkProviderResponse:
    return ChunkProviderResponse.model_validate(
        {
            "contract_version": "1.0",
            "provider": "topic11",
            "provider_version": "mock-1",
            "chunks": list(chunks),
            "warnings": [],
            "trace": {},
        }
    )


def test_internal_provider_is_offline_default() -> None:
    resolver = ChunkProviderResolver(settings=Settings(offline_mode=True))
    options = _options(provider="internal")

    result = resolver.resolve(
        canonical=_canonical(), options=options, legacy_chunks=_legacy_chunks()
    )

    assert result.trace.requested_provider == "internal"
    assert result.trace.used_provider == "internal"
    assert result.trace.external_requested is False
    assert result.trace.fallback_used is False
    assert result.chunks


def test_internal_provider_chunk_ids_use_canonical_task_id() -> None:
    canonical = _canonical()
    result = ChunkProviderResolver(settings=Settings(offline_mode=True)).resolve(
        canonical=canonical,
        options=_options(provider="internal"),
        legacy_chunks=_legacy_chunks(),
    )

    assert result.chunks
    assert all(
        chunk["chunk_id"].startswith(f"chunk_{canonical.task_id}_")
        for chunk in result.chunks
    )
    assert all(canonical.doc_id not in chunk["chunk_id"] for chunk in result.chunks)


def test_topic11_request_contract_carries_real_task_id() -> None:
    canonical = _canonical()
    request = ChunkProviderResolver.build_request(canonical, _options())
    contract = json.loads(
        (ROOT / "contracts" / "schemas" / "topic11_chunk_request.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert request.task_id == canonical.task_id
    assert request.contract_version == "1.1"
    assert contract["properties"]["contract_version"]["const"] == "1.1"
    assert "task_id" in contract["required"]
    assert contract["properties"]["task_id"]["minLength"] == 1


def test_topic11_request_rejects_empty_task_id_at_runtime() -> None:
    payload = ChunkProviderResolver.build_request(
        _canonical(), _options()
    ).model_dump(mode="json")
    payload["task_id"] = ""

    with pytest.raises(ValidationError):
        ChunkProviderRequest.model_validate(payload)


def test_topic11_request_v1_0_cannot_claim_v1_1_shape() -> None:
    payload = ChunkProviderResolver.build_request(
        _canonical(), _options()
    ).model_dump(mode="json")
    payload["contract_version"] = "1.0"

    with pytest.raises(ValidationError):
        ChunkProviderRequest.model_validate(payload)


def test_topic11_valid_response_is_used() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-1",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
                "entity_ids": ["org:openai"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert [chunk["chunk_id"] for chunk in result.chunks] == [
        "external-1",
        "external-table",
    ]
    assert result.trace.used_provider == "topic11"
    assert result.trace.external_used is True
    assert result.trace.validation_passed is True
    assert result.trace.latency_ms == 7


@pytest.mark.parametrize(
    "error_code",
    ["topic11_timeout", "topic11_http_error", "topic11_response_invalid"],
)
def test_provider_failures_fallback_to_internal(error_code: str) -> None:
    resolver = ChunkProviderResolver(
        settings=Settings(), external_provider=FakeProvider(error=error_code)
    )

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.used_provider == "internal"
    assert result.trace.fallback_used is True
    assert result.trace.fallback_reason == error_code
    assert result.trace.external_used is False


def test_unknown_source_block_is_rejected_and_falls_back() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "bad",
                "text": "Unknown text",
                "source_block_ids": ["unknown"],
            }
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.used_provider == "internal"
    assert result.trace.fallback_reason == "topic11_unknown_source_block"


def test_hallucinated_chunk_text_is_rejected_and_falls_back() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "bad",
                "text": "A fact that is absent from the source.",
                "source_block_ids": ["b1"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_chunk_text_not_derivable"
    assert result.trace.used_provider == "internal"


def test_unknown_entity_id_is_rejected() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "bad",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
                "entity_ids": ["org:invented"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_unknown_entity_id"


def test_missing_protected_table_is_rejected() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "only-text",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
            }
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_protected_block_missing"


def test_missing_ordinary_nonempty_paragraph_is_rejected() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            }
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_canonical_block_missing"


def test_whitespace_chunk_does_not_cover_ordinary_paragraph() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-1",
                "text": " \n\t",
                "source_block_ids": ["b1"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_chunk_text_empty"


def test_protected_table_text_must_be_preserved_exactly() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-1",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_protected_block_integrity"


def test_protected_table_newlines_and_indentation_cannot_change() -> None:
    canonical = _canonical()
    canonical.blocks[1].text = "Field:\n  Value"
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-1",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
            },
            {
                "chunk_id": "external-table",
                "text": "Field: Value",
                "source_block_ids": ["table1"],
            },
        )
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    result = resolver.resolve(
        canonical=canonical, options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_protected_block_integrity"


def test_protected_block_cannot_be_excluded_by_registered_rule() -> None:
    external = FakeProvider(
        _response(
            {
                "chunk_id": "external-1",
                "text": "OpenAI published the notice.",
                "source_block_ids": ["b1"],
            }
        )
    )
    options = _options(
        block_exclusion_rules=[{"rule_id": "exclude-v1"}],
        block_exclusions=[
            {
                "block_id": "table1",
                "exclusion_reason": "attempted protected exclusion",
                "rule_id": "exclude-v1",
            }
        ],
    )
    resolver = ChunkProviderResolver(settings=Settings(), external_provider=external)

    with pytest.raises(ChunkProviderError) as exc_info:
        resolver.resolve(
            canonical=_canonical(), options=options, legacy_chunks=_legacy_chunks()
        )

    assert exc_info.value.code == "topic11_protected_block_exclusion"


def test_strict_provider_mode_returns_failure_without_fallback() -> None:
    resolver = ChunkProviderResolver(
        settings=Settings(),
        external_provider=FakeProvider(error="topic11_timeout"),
    )

    with pytest.raises(ChunkProviderError) as exc:
        resolver.resolve(
            canonical=_canonical(),
            options=_options(strict_provider=True),
            legacy_chunks=_legacy_chunks(),
        )

    assert exc.value.code == "topic11_timeout"


def test_missing_endpoint_configuration_falls_back_with_clear_reason() -> None:
    resolver = ChunkProviderResolver(settings=Settings(topic11_base_url=""))

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_endpoint_missing"
    assert result.trace.used_provider == "internal"


def test_offline_mode_falls_back_without_network() -> None:
    resolver = ChunkProviderResolver(
        settings=Settings(offline_mode=True, topic11_base_url="https://example.invalid")
    )

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert result.trace.fallback_reason == "topic11_offline"


def test_http_provider_maps_timeout_and_http_errors_without_secret() -> None:
    secret = "topic11-secret-value"
    request = ChunkProviderResolver.build_request(_canonical(), _options())

    def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(secret)

    timeout_client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
    timeout_provider = Topic11HttpChunkProvider(
        Settings(
            topic11_base_url="https://topic11.invalid",
            topic11_api_key=secret,
        ),
        client=timeout_client,
    )
    with pytest.raises(ChunkProviderError) as timeout_exc:
        timeout_provider.provide(request)
    assert timeout_exc.value.code == "topic11_timeout"
    assert secret not in str(timeout_exc.value)

    error_client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(500))
    )
    error_provider = Topic11HttpChunkProvider(
        Settings(
            topic11_base_url="https://topic11.invalid",
            topic11_api_key=secret,
        ),
        client=error_client,
    )
    with pytest.raises(ChunkProviderError) as http_exc:
        error_provider.provide(request)
    assert http_exc.value.code == "topic11_http_error"
    assert secret not in str(http_exc.value)


def test_http_provider_rejects_invalid_response_schema() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json={"contract_version": "1.0"})
        )
    )
    provider = Topic11HttpChunkProvider(
        Settings(topic11_base_url="https://topic11.invalid"), client=client
    )

    with pytest.raises(ChunkProviderError) as exc:
        provider.provide(ChunkProviderResolver.build_request(_canonical(), _options()))

    assert exc.value.code == "topic11_response_invalid"


def test_provider_trace_never_contains_api_key() -> None:
    secret = "topic11-do-not-leak"
    resolver = ChunkProviderResolver(
        settings=Settings(topic11_api_key=secret),
        external_provider=FakeProvider(error="topic11_http_error"),
    )

    result = resolver.resolve(
        canonical=_canonical(), options=_options(), legacy_chunks=_legacy_chunks()
    )

    assert secret not in json.dumps(result.trace.model_dump(mode="json"))
