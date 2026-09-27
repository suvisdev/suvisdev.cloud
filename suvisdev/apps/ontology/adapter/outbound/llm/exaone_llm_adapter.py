"""EXAONE-3.5-7.8B(Ollama) 어댑터 — 홈 포트폴리오 채팅의 답변 LLM(HubLlmPort 구현체).

2026-09-27 사용자 결정: 홈 AI 채팅의 오케스트레이터는 로컬 EXAONE 7.8B. 문서 근거를
프롬프트에 넣어 답하므로 컨텍스트를 8192로 명시한다(ollama 기본 4096이면 근거가 잘린다).
노트북 RTX 4060 실측(09-27): num_ctx 8192에서 5.7GB, lora-server(2.4GB)와 동시 상주 가능,
콜드 로드 5s·근거 2,240토큰 응답 7s. keep_alive를 짧게(5m) 둬 mova 쪽 모델에 VRAM을 돌려준다.
OrchestratorError는 HubRagError로 감싼다 — FallbackHubLlmAdapter(→Gemini)가 그것만 잡는다.
"""

from __future__ import annotations

import asyncio
import os

from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator, SuvisdevOrchestratorError
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

_DEFAULT_MODEL = os.getenv("PORTFOLIO_LLM_MODEL", "exaone3.5:7.8b")
_DEFAULT_KEEP_ALIVE = os.getenv("PORTFOLIO_LLM_KEEP_ALIVE", "5m")
_NUM_CTX = 8192


class ExaoneLlmAdapter(HubLlmPort):
    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        keep_alive: str = _DEFAULT_KEEP_ALIVE,
        num_ctx: int = _NUM_CTX,
    ) -> None:
        self._orchestrator = SuvisdevOrchestrator(model=model, keep_alive=keep_alive)
        self._num_ctx = num_ctx

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            return await asyncio.to_thread(
                self._orchestrator.generate,
                prompt,
                system=system,
                temperature=0,
                num_ctx=self._num_ctx,
            )
        except SuvisdevOrchestratorError as e:
            raise HubRagError(e.detail, status_code=e.status_code) from e
