from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

# nomic-embed-text 기준 차원. exaone3.5는 Ollama capabilities가 completion뿐이라
# 임베딩 전용 모델을 쓴다 (dispatch/embedding_port.py와 동일 결정, 2026-07-02 확정 사항 재사용).
EMBEDDING_DIM: Final[int] = 768


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
