from __future__ import annotations

from execsuite.app.dtos.langchain_chat_dto import LangchainChatDto
from execsuite.app.ports.output.langchain_chat_engine_port import LangchainChatEnginePort
from execsuite.app.ports.output.langchain_chat_errors import LangchainChatError
from ontology.app.dtos.semantic_router_dto import SemanticRouteCommand
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.app.ports.output.hub_rag_errors import HubRagError


def _last_user_question(messages: list[dict[str, str]]) -> str:
    return next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")


class LangchainInteractor:
    """langchain_chat_router → 입력 포트.

    ontology의 semantic_router_interactor로 의도(destination/entities)를 먼저
    판단하고, 그 결과를 LangChain 챗봇 엔진(langchain_chat_engine_repository)에
    넘겨 최종 답변을 생성한다.
    """

    def __init__(
        self, *, semantic_router: SemanticRouterUseCase, chat_engine: LangchainChatEnginePort
    ) -> None:
        self._semantic_router = semantic_router
        self._chat_engine = chat_engine

    async def chat(self, *, messages: list[dict[str, str]], system: str | None) -> LangchainChatDto:
        question = _last_user_question(messages)
        try:
            route = await self._semantic_router.route(SemanticRouteCommand(question=question))
        except HubRagError as e:
            raise LangchainChatError(
                f"의도 판단 중 오류가 발생했습니다: {e.detail}", status_code=e.status_code
            ) from e
        reply = await self._chat_engine.generate(
            messages=messages,
            destination=route.destination,
            entities=route.entities,
            grounding=route.answer,
        )
        return LangchainChatDto(reply=reply)
