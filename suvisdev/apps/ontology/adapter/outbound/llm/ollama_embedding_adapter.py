from __future__ import annotations

import os
from typing import cast

import httpx

from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

_OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_DEFAULT_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class OllamaEmbeddingAdapter(EmbeddingPort):
    """dispatch/adapter/outbound/llm/ollama_embedding_adapter.py와 동일 구현.

    Hub는 Spoke(dispatch)를 import할 수 없어 자체 보유한다 (스타-토폴로지 규칙).
    """

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        base_url: str = _OLLAMA_BASE,
        timeout: float = 30.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": text},
                )
        except httpx.TimeoutException as e:
            raise HubRagError("Ollama 임베딩 응답 타임아웃", status_code=504) from e
        except httpx.TransportError as e:
            raise HubRagError(f"Ollama 서버에 연결할 수 없습니다: {e!s}", status_code=503) from e

        if r.status_code != 200:
            raise HubRagError(
                f"Ollama 임베딩 호출 실패 (HTTP {r.status_code}): {r.text[:200]}",
                status_code=502,
            )

        embeddings = r.json().get("embeddings")
        if not embeddings or not embeddings[0]:
            raise HubRagError("Ollama가 빈 임베딩을 반환했습니다.", status_code=502)
        return cast(list[float], embeddings[0])
