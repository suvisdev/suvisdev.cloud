from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_watchlist_pg_repository import WatchlistPgRepository
from mova.app.ports.input.market_watchlist_use_case import WatchlistUseCase
from mova.app.use_cases.market_watchlist_interactor import WatchlistInteractor


def get_watchlist_use_case(
    db: AsyncSession = Depends(get_mova_db),
) -> WatchlistUseCase:
    return WatchlistInteractor(repository=WatchlistPgRepository(session=db))
