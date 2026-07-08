from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

# nomic-embed-text embedding_length. exaone3.5:2.4b은 Ollama capabilities가
# "completion"뿐이라 /api/embed 호출이 항상 실패해 임베딩 전용 모델로 교체 (2026-07-02).
EMBEDDING_DIM: Final[int] = 768


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
