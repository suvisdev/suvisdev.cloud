from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from gildle.adapter.outbound.pg.push_token_pg_repository import PushTokenPgRepository
from gildle.adapter.outbound.pg.walk_pg_repository import WalkPgRepository
from gildle.app.ports.input.account_data_use_case import AccountDataUseCase
from gildle.app.use_cases.account_data_interactor import AccountDataInteractor


def get_account_data_use_case(db: AsyncSession = Depends(get_db)) -> AccountDataUseCase:
    return AccountDataInteractor(
        walks=WalkPgRepository(session=db), push_tokens=PushTokenPgRepository(session=db)
    )
