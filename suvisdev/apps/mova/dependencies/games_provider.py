from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.games_pg_repository import GamesPgRepository
from mova.app.ports.input.games_use_case import GamesUseCase
from mova.app.use_cases.games_interactor import GamesInteractor


def get_games_use_case(
    db: AsyncSession = Depends(get_mova_db),
) -> GamesUseCase:
    return GamesInteractor(repository=GamesPgRepository(session=db))
