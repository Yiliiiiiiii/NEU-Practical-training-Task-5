from app.engines.chunk_engine import ChunkEngine
from app.schemas.canonical import CanonicalModel
from app.schemas.chunks import ChunksJSON


class ChunksRenderer:
    def __init__(self) -> None:
        self.engine = ChunkEngine()

    def render(
        self,
        canonical: CanonicalModel,
        chunk_size: int = 500,
    ) -> ChunksJSON:
        return self.engine.chunk(canonical, chunk_size=chunk_size)
