"""Qwen2.5-1.5B-Instruct(Ollama) 직접 호출 어댑터 — HubLlmPort 구현체.

시맨틱 라우터의 분류(routing)·RAG 답변 두 역할을 이 모델 하나로 겸한다("1인 2역").
QLoRA 파인튜닝 없이 역할별 시스템 프롬프트만 바꿔 끼우는 것으로 충분하다 — PoC
단계에서 1.5B Instruct 모델도 JSON 스키마 지시를 충분히 따르고, 파인튜닝 없이
프롬프트 튜닝만으로 빠르게 검증할 수 있다.

core.lol.T1MidFakerOrchestrator(exaone3.5:7.8b 전용으로 보이지만 실제로는 model
인자로 어떤 Ollama 모델이든 띄울 수 있음)를 그대로 재사용한다. 기존 EXAONE AWQ
직접 서빙(awq_server, gptqmodel) 대신 이 경로를 쓰는 이유는 VRAM 여유 부족 —
로컬 GPU(8GB)에서 AWQ 서빙(~5.9GB) + 다른 작업을 같이 돌리기엔 빠듯하다.
"""

from __future__ import annotations

import asyncio

from core.lol.t1_mid_faker_orchestrator import FakerOrchestratorError, T1MidFakerOrchestrator
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

_QWEN_MODEL = "qwen2.5:1.5b"


class QwenLlmAdapter(HubLlmPort):
    def __init__(self) -> None:
        self._orchestrator = T1MidFakerOrchestrator(model=_QWEN_MODEL)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            return await asyncio.to_thread(self._orchestrator.generate, prompt, system=system)
        except FakerOrchestratorError as e:
            raise HubRagError(e.detail, status_code=e.status_code) from e
