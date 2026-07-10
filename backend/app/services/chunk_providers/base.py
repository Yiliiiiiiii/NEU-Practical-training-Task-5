from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.chunk_provider import (
    ChunkProviderRequest,
    ChunkProviderResponse,
    ChunkProviderTrace,
)


class ChunkProviderError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ChunkProviderInvocation:
    response: ChunkProviderResponse
    latency_ms: int | None = None


@dataclass(frozen=True)
class ChunkProviderResult:
    chunks: list[dict]
    trace: ChunkProviderTrace


class ChunkProvider(Protocol):
    def provide(self, request: ChunkProviderRequest) -> ChunkProviderInvocation: ...
