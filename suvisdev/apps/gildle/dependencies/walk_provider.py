from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from gildle.adapter.outbound.pg.walk_pg_repository import WalkPgRepository
from gildle.app.ports.input.walk_use_case import WalkUseCase
from gildle.app.use_cases.walk_interactor import WalkInteractor


def get_walk_use_case(db: AsyncSession = Depends(get_db)) -> WalkUseCase:
    return WalkInteractor(repository=WalkPgRepository(session=db))
