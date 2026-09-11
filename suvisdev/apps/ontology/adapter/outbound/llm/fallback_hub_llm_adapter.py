"""HubLlmPort 폴백 조합 — primary 실패 시 fallback으로 한 번 더 시도.

Ollama(Qwen)가 없는 배포 환경에선 인텐트 분류가 항상 호출 실패 → 기본값(recommend)으로
새던 잠복 결함(2026-08-28 3트랙 배포 실측에서 발견 — 기본값이 rag이던 시절엔
증상이 안 보였다). 추천 어댑터의 LoRA→Gemini 폴백과 같은 철학으로, 분류도
Qwen(로컬 Ollama)→Gemini(원격 API) 폴백을 태운다.
"""

from __future__ import annotations

import logging

from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

logger = logging.getLogger(__name__)


class FallbackHubLlmAdapter(HubLlmPort):
    def __init__(self, *, primary: HubLlmPort, fallback: HubLlmPort) -> None:
        self._primary = primary
        self._fallback = fallback

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            return await self._primary.generate(prompt, system=system)
        except HubRagError as e:
            logger.warning(
                "[FallbackHubLlmAdapter] primary 실패 → fallback 시도 | detail=%s", e.detail
            )
            return await self._fallback.generate(prompt, system=system)
