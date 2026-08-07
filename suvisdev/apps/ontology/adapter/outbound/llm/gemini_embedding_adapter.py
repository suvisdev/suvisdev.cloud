from __future__ import annotations

import asyncio
import os

from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EMBEDDING_DIM, EmbeddingPort

_DEFAULT_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")


class GeminiEmbeddingAdapter(EmbeddingPort):
    """OllamaEmbeddingAdapter의 EC2용 대체 — Ollama가 없는 환경에서 쓴다.

    `gemini-embedding-001`의 기본 차원은 3072지만 `hub_knowledge.embedding`
    컬럼이 768(pgvector `Vector(768)`)이라 `output_dimensionality`로 맞춘다.
    MRL 절단이라 반환 벡터의 L2 norm이 1이 아니지만, 검색이
    `cosine_distance`(스케일 불변)만 쓰므로 순위에 영향이 없어 재정규화하지
    않는다.

    **Ollama(nomic-embed-text)와 의미 공간이 달라 벡터가 호환되지 않는다** —
    임베딩 백엔드를 바꾸면 기존 hub_knowledge 전량을 재임베딩해야 한다
    (`scripts/ingest_hub_knowledge.py --embedding-backend gemini --reset`).
    """

    def __init__(self, *, model: str = _DEFAULT_MODEL, dimensions: int = EMBEDDING_DIM) -> None:
        self._model = model
        self._dimensions = dimensions

    def _embed_sync(self, text: str) -> list[float]:
        from core.matrix.vauly_keymaker_secret_manager import get_keymaker

        keymaker = get_keymaker()
        if not keymaker.gemini_ready:
            raise HubRagError("GEMINI_API_KEY가 설정되지 않았습니다.", status_code=503)

        # Keymaker가 import 시점에 genai.configure(api_key=...)를 이미 끝냈다.
        import google.generativeai as genai

        try:
            result = genai.embed_content(
                model=self._model,
                content=text,
                output_dimensionality=self._dimensions,
            )
        except Exception as e:
            raise HubRagError(f"Gemini 임베딩 호출 실패: {e!s}", status_code=502) from e

        vector = result.get("embedding")
        if not vector:
            raise HubRagError("Gemini가 빈 임베딩을 반환했습니다.", status_code=502)
        return list(vector)

    async def embed(self, text: str) -> list[float]:
        # genai.embed_content는 동기 호출 — 이벤트 루프를 막지 않도록 스레드로 위임한다.
        return await asyncio.to_thread(self._embed_sync, text)
