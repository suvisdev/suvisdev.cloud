from __future__ import annotations

from ontology.app.dtos.semantic_router_dto import SemanticRouteCommand
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.app.ports.output.hub_rag_errors import HubRagError
from execsuite.app.dtos.rangchain_chat_dto import RangchainChatDto
from execsuite.app.ports.output.rangchain_chat_engine_port import RangchainChatEnginePort
from execsuite.app.ports.output.rangchain_chat_errors import RangchainChatError


def _last_user_question(messages: list[dict[str, str]]) -> str:
    return next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")


class RangchainInteractor:
    """rangchain_chat_router → 입력 포트.

    ontology의 semantic_router_interactor로 의도(destination/entities)를 먼저
    판단하고, 그 결과를 LangChain 챗봇 엔진(rangchain_chat_engine_repository)에
    넘겨 최종 답변을 생성한다.
    """

    def __init__(
        self, *, semantic_router: SemanticRouterUseCase, chat_engine: RangchainChatEnginePort
    ) -> None:
        self._semantic_router = semantic_router
        self._chat_engine = chat_engine

    async def chat(self, *, messages: list[dict[str, str]], system: str | None) -> RangchainChatDto:
        question = _last_user_question(messages)
        try:
            route = await self._semantic_router.route(SemanticRouteCommand(question=question))
        except HubRagError as e:
            raise RangchainChatError(
                f"의도 판단 중 오류가 발생했습니다: {e.detail}", status_code=e.status_code
            ) from e
        reply = await self._chat_engine.generate(
            messages=messages,
            destination=route.destination,
            entities=route.entities,
            grounding=route.answer,
        )
        return RangchainChatDto(reply=reply)
