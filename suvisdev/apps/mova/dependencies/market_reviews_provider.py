"""리뷰 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.market_reviews_pg_repository import ReviewsPgRepository
from mova.app.ports.input.market_reviews_use_case import ReviewsUseCase
from mova.app.ports.output.market_reviews_repository import ReviewsRepositoryPort
from mova.app.use_cases.market_reviews_interactor import ReviewsInteractor


def get_reviews_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> ReviewsRepositoryPort:
    return ReviewsPgRepository(session=db)


def get_reviews_use_case(
    repository: ReviewsRepositoryPort = Depends(get_reviews_repository),
) -> ReviewsUseCase:
    return ReviewsInteractor(repository=repository)


get_market_reviews_use_case = get_reviews_use_case
