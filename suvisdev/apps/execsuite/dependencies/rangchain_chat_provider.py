from __future__ import annotations

from fastapi import Depends

from ontology.app.ports.input.semantic_router_use_case import SemanticRouterUseCase
from ontology.dependencies.semantic_router_provider import get_semantic_router_use_case
from execsuite.adapter.outbound.repositories.rangchain_chat_engine_repository import (
    RangchainChatEngineRepository,
)
from execsuite.app.ports.input.rangchain_chat_use_case import RangchainChatUseCase
from execsuite.app.ports.output.rangchain_chat_engine_port import RangchainChatEnginePort
from execsuite.app.use_case.rangchain_interactor import RangchainInteractor


def get_rangchain_chat_engine_port() -> RangchainChatEnginePort:
    return RangchainChatEngineRepository()


def get_rangchain_chat_use_case(
    semantic_router: SemanticRouterUseCase = Depends(get_semantic_router_use_case),
    chat_engine: RangchainChatEnginePort = Depends(get_rangchain_chat_engine_port),
) -> RangchainChatUseCase:
    return RangchainInteractor(semantic_router=semantic_router, chat_engine=chat_engine)
