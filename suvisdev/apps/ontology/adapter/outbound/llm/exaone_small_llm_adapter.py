"""EXAONE-3.5-2.4B(Ollama) 호출 어댑터 — HubLlmPort 구현체(분류·하베스터 파싱·짧은 RAG 답변용 소형).
2026-09-27 개명: 구 qwen_llm_adapter/QwenLlmAdapter — 09-17에 모델은 EXAONE으로 바꿨는데 이름만 Qwen으로
남아 있었다(사용자 지적 "qwen은 어디서 쓰나"). 프로젝트의 로컬 LLM은 EXAONE(2.4B·7.8B·LoRA)뿐이다.

2026-09-17: qwen2.5:1.5b → exaone3.5:2.4b 전환(사용자 결정 — 로컬 모델을 EXAONE으로
통일). 노트북에 qwen이 없어 매 요청 404 → Gemini 폴백이던 상태였다. 실채팅 질문
114건(결정론 가드 제외) 실측: Gemini 분류와 90% 일치, 평균 0.3~0.6s. 분류가
흔들리지 않게 temperature 0 고정(exaone Modelfile 기본값은 1).

시맨틱 라우터의 분류(routing)·RAG 답변 두 역할을 이 모델 하나로 겸한다("1인 2역").
QLoRA 파인튜닝 없이 역할별 시스템 프롬프트만 바꿔 끼우는 것으로 충분하다 — PoC
단계에서 1.5B Instruct 모델도 JSON 스키마 지시를 충분히 따르고, 파인튜닝 없이
프롬프트 튜닝만으로 빠르게 검증할 수 있다.

core.lol.SuvisdevOrchestrator(exaone3.5:7.8b 전용으로 보이지만 실제로는 model
인자로 어떤 Ollama 모델이든 띄울 수 있음)를 그대로 재사용한다. 기존 EXAONE AWQ
직접 서빙(awq_server, gptqmodel) 대신 이 경로를 쓰는 이유는 VRAM 여유 부족 —
로컬 GPU(8GB)에서 AWQ 서빙(~5.9GB) + 다른 작업을 같이 돌리기엔 빠듯하다.
"""

from __future__ import annotations

import asyncio

from core.lol.suvisdev_orchestrator import SuvisdevOrchestrator, SuvisdevOrchestratorError
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

_EXAONE_SMALL_MODEL = "exaone3.5:2.4b"


class ExaoneSmallLlmAdapter(HubLlmPort):
    def __init__(self) -> None:
        self._orchestrator = SuvisdevOrchestrator(model=_EXAONE_SMALL_MODEL)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            return await asyncio.to_thread(
                self._orchestrator.generate, prompt, system=system, temperature=0
            )
        except SuvisdevOrchestratorError as e:
            raise HubRagError(e.detail, status_code=e.status_code) from e
