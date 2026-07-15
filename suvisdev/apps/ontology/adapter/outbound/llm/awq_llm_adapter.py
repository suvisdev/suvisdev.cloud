"""EXAONE-3.5-7.8B-Instruct-AWQ 직접 서빙 어댑터 — HubLlmPort 구현체.

core/lol의 공용 오케스트레이터(AwqExaoneOrchestrator)를 감싸기만 한다.
mova의 ExaoneRecommendationAdapter가 T1MidFakerOrchestrator를 감싸는 것과 동일 패턴.
"""

from __future__ import annotations

import asyncio

from core.lol.awq_exaone_orchestrator import AwqExaoneOrchestrator, AwqOrchestratorError
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError


class AwqLlmAdapter(HubLlmPort):
    def __init__(self) -> None:
        self._orchestrator = AwqExaoneOrchestrator()

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            return await asyncio.to_thread(self._orchestrator.generate, prompt, system=system)
        except AwqOrchestratorError as e:
            raise HubRagError(e.detail, status_code=e.status_code) from e
