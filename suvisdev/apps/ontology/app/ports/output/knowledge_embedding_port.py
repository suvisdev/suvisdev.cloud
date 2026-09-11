from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

# nomic-embed-text 기준 차원. exaone3.5는 Ollama capabilities가 completion뿐이라
# 임베딩 전용 모델을 쓴다 (dispatch/embedding_port.py와 동일 결정, 2026-07-02 확정 사항 재사용).
# 2026-09-11 bge-m3 전환(1024) — eval_embedding_models.py 실측으로 한국어
# recall@8 0.390(nomic)→0.860. 바꾸면 hub_knowledge 마이그레이션(20260911_0001)
# + 전체 재임베딩(ingest_hub_knowledge.py --reset)이 필수다.
EMBEDDING_DIM: Final[int] = 1024


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
