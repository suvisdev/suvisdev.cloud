"""시맨틱 인텐트 게이트웨이의 3번째 분기 — RAG/CRUD가 아닌 일반 질의를 Gemini로 응답한다.

게이트웨이는 들어온 질문을 RAG(HubRagUseCase)/CRUD(각 Spoke)/범용 응답(여기) 세 갈래로
분류해 라우팅한다. 이 Interactor는 그중 세 번째 갈래만 담당한다.
"""

from __future__ import annotations

import logging

from ontology.app.dtos.mycroft_dto import MycroftAnswerDto, MycroftAskCommand
from ontology.app.ports.input.mycroft_use_case import MycroftUseCase
from ontology.app.ports.output.hub_llm_port import HubLlmPort
from ontology.app.ports.output.hub_rag_errors import HubRagError

logger = logging.getLogger(__name__)


class MycroftInteractor(MycroftUseCase):
    def __init__(self, *, llm: HubLlmPort) -> None:
        self._llm = llm

    async def ask(self, command: MycroftAskCommand) -> MycroftAnswerDto:
        try:
            text = await self._llm.generate(command.question, system=command.system)
        except HubRagError as e:
            logger.warning("[MycroftInteractor] Gemini 호출 실패 | detail=%s", e.detail)
            raise
        return MycroftAnswerDto(text=text)
