"""picks DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_picks_pg_repository import PicksPgRepository
from mova.app.ports.input.market_picks_use_case import PicksUseCase
from mova.app.ports.output.market_picks_repository import PicksRepositoryPort
from mova.app.use_cases.market_picks_interactor import PicksInteractor


def get_picks_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> PicksRepositoryPort:
    return PicksPgRepository(session=db)


def get_picks_use_case(
    repository: PicksRepositoryPort = Depends(get_picks_repository),
) -> PicksUseCase:
    return PicksInteractor(repository=repository)
