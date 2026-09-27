from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from gildle.adapter.outbound.pg.push_token_pg_repository import PushTokenPgRepository
from gildle.app.ports.input.push_token_use_case import PushTokenUseCase
from gildle.app.use_cases.push_token_interactor import PushTokenInteractor


def get_push_token_use_case(db: AsyncSession = Depends(get_db)) -> PushTokenUseCase:
    return PushTokenInteractor(repository=PushTokenPgRepository(session=db))
