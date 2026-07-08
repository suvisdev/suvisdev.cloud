"""검색 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.studio_search_pg_repository import SearchPgRepository
from mova.app.ports.input.studio_search_use_case import SearchUseCase
from mova.app.ports.output.studio_search_repository import SearchRepositoryPort
from mova.app.use_cases.studio_search_interactor import SearchInteractor


def get_search_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> SearchRepositoryPort:
    return SearchPgRepository(session=db)


def get_search_use_case(
    repository: SearchRepositoryPort = Depends(get_search_repository),
) -> SearchUseCase:
    return SearchInteractor(repository=repository)


get_studio_search_use_case = get_search_use_case
