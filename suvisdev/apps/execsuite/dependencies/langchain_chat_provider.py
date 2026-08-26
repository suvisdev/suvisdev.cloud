from __future__ import annotations

from fastapi import Depends

from execsuite.adapter.outbound.repositories.langchain_chat_engine_repository import (
    LangchainChatEngineRepository,
)
from execsuite.app.ports.input.langchain_chat_use_case import LangchainChatUseCase
from execsuite.app.ports.output.langchain_chat_engine_port import LangchainChatEnginePort
from execsuite.app.use_case.langchain_interactor import LangchainInteractor
from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.dependencies.semantic_router_provider import get_semantic_router_use_case


def get_langchain_chat_engine_port() -> LangchainChatEnginePort:
    return LangchainChatEngineRepository()


def get_langchain_chat_use_case(
    semantic_router: SemanticRouterUseCase = Depends(get_semantic_router_use_case),
    chat_engine: LangchainChatEnginePort = Depends(get_langchain_chat_engine_port),
) -> LangchainChatUseCase:
    return LangchainInteractor(semantic_router=semantic_router, chat_engine=chat_engine)
