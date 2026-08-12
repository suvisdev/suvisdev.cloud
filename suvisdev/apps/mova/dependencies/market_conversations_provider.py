"""대화 스레드 DI."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_conversations_pg_repository import (
    ConversationsPgRepository,
)
from mova.app.ports.input.market_conversations_use_case import ConversationsUseCase
from mova.app.ports.output.market_conversations_repository import ConversationsRepository
from mova.app.use_cases.market_conversations_interactor import ConversationsInteractor


def get_conversations_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> ConversationsRepository:
    return ConversationsPgRepository(session=db)


def get_conversations_use_case(
    repository: ConversationsRepository = Depends(get_conversations_repository),
) -> ConversationsUseCase:
    return ConversationsInteractor(repository=repository)
