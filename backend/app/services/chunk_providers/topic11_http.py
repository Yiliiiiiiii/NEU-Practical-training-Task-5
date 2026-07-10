from __future__ import annotations

from time import perf_counter

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas.chunk_provider import ChunkProviderRequest, ChunkProviderResponse
from app.services.chunk_providers.base import (
    ChunkProviderError,
    ChunkProviderInvocation,
)


class Topic11HttpChunkProvider:
    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client

    def provide(self, request: ChunkProviderRequest) -> ChunkProviderInvocation:
        if self.settings.offline_mode:
            raise ChunkProviderError("topic11_offline")
        if not self.settings.topic11_base_url.strip():
            raise ChunkProviderError("topic11_endpoint_missing")

        headers = {"Content-Type": "application/json"}
        if self.settings.topic11_api_key:
            headers["Authorization"] = f"Bearer {self.settings.topic11_api_key}"
        url = self.settings.topic11_base_url.rstrip("/") + "/chunks"
        started = perf_counter()
        try:
            if self.client is not None:
                response = self.client.post(
                    url,
                    json=request.model_dump(mode="json"),
                    headers=headers,
                    timeout=self.settings.topic11_timeout_seconds,
                )
            else:
                with httpx.Client() as client:
                    response = client.post(
                        url,
                        json=request.model_dump(mode="json"),
                        headers=headers,
                        timeout=self.settings.topic11_timeout_seconds,
                    )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise ChunkProviderError("topic11_timeout") from None
        except httpx.HTTPError:
            raise ChunkProviderError("topic11_http_error") from None
        latency_ms = max(0, round((perf_counter() - started) * 1000))
        try:
            parsed = ChunkProviderResponse.model_validate(response.json())
        except (ValidationError, ValueError, TypeError):
            raise ChunkProviderError("topic11_response_invalid") from None
        if parsed.provider != "topic11":
            raise ChunkProviderError("topic11_response_invalid")
        return ChunkProviderInvocation(response=parsed, latency_ms=latency_ms)
