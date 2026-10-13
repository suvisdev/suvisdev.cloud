from __future__ import annotations

import os
from typing import cast

import httpx

from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.app.ports.output.knowledge_embedding_port import EmbeddingPort

# 임베딩은 집컴 올라마(CPU)에 고정한다(2026-10-07): 질문 한 줄 임베딩은 집컴 직접 약 0.1초, 노트북 GPU를
# 중계기·Tailscale로 거치면 약 0.35초 — 네트워크 왕복이 GPU 이득보다 크다. 집컴 .env 는 자기 올라마(:11434),
# 노트북 .env 는 desktop-link 의 :21435(집컴 올라마). 비우면 OLLAMA_BASE_URL(중계기)을 쓴다.
_OLLAMA_BASE: str = (
    os.getenv("OLLAMA_EMBED_URL") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
)
# 2026-09-11 nomic-embed-text→bge-m3(1024차원, 접두사 불요) — 한국어 검색
# recall@8 0.390→0.860 실측(scripts/eval_embedding_models.py). 서빙 노드에
# `ollama pull bge-m3` + hub 재임베딩이 선행돼야 한다(RS_TEACHER_LOOP.md).
# dispatch의 동명 어댑터는 자체 768 공간이라 그대로 nomic을 쓴다.
_DEFAULT_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
# core.lol.ollama_client 와 같은 값. 안 보내면 올라마 기본 5분 뒤 bge-m3 가 내려가 쉬었다 온 첫 질문이
# 다시 올리느라 2초 넘게 더 걸렸다(2026-10-07 노트북 실측: /api/embed 2.25초, 상주 시 0.15초).
_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")


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
        keep_alive: str = _KEEP_ALIVE,
    ) -> None:
        self._model = model
        self._keep_alive = keep_alive
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self._base_url}/api/embed",
                    json={"model": self._model, "input": text, "keep_alive": self._keep_alive},
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
