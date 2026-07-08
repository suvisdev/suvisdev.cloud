"""영화 DI — Repository + UseCase 조립."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.movies_pg_repository import MoviesPgRepository
from mova.app.ports.input.studio_movies_use_case import MoviesUseCase
from mova.app.ports.output.movies_repository import MoviesRepositoryPort
from mova.app.use_cases.studio_movies_interactor import MoviesInteractor


def get_movies_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> MoviesRepositoryPort:
    return MoviesPgRepository(session=db)


def get_movies_use_case(
    repository: MoviesRepositoryPort = Depends(get_movies_repository),
) -> MoviesUseCase:
    return MoviesInteractor(repository=repository)


# 기존 stub 의존성 이름 호환 (다른 파일에서 참조 중일 경우 대비)
get_studio_movies_use_case = get_movies_use_case
