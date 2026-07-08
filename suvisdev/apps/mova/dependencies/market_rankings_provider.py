"""랭킹 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_rankings_pg_repository import RankingsPgRepository
from mova.app.ports.input.market_rankings_use_case import (
    GenerateChatTrendRankingUseCase,
    RankingsUseCase,
)
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.app.use_cases.market_rankings_interactor import (
    GenerateChatTrendRankingInteractor,
    RankingsInteractor,
)


def get_rankings_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> RankingsRepositoryPort:
    return RankingsPgRepository(session=db)


def get_rankings_use_case(
    repository: RankingsRepositoryPort = Depends(get_rankings_repository),
) -> RankingsUseCase:
    return RankingsInteractor(repository=repository)


def get_generate_chat_trend_ranking_use_case(
    repository: RankingsRepositoryPort = Depends(get_rankings_repository),
) -> GenerateChatTrendRankingUseCase:
    return GenerateChatTrendRankingInteractor(repository=repository)


get_market_rankings_use_case = get_rankings_use_case
