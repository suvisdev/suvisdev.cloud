"""배우 DI — Repository + UseCase 조립."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.studio_actors_pg_repository import ActorsPgRepository
from mova.app.ports.input.studio_actors_use_case import ActorsUseCase
from mova.app.ports.output.studio_actors_repository import ActorsRepositoryPort
from mova.app.use_cases.studio_actors_interactor import ActorsInteractor


def get_actors_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> ActorsRepositoryPort:
    return ActorsPgRepository(session=db)


def get_actors_use_case(
    repository: ActorsRepositoryPort = Depends(get_actors_repository),
) -> ActorsUseCase:
    return ActorsInteractor(repository=repository)


# 기존 stub 이름 호환
get_studio_actors_use_case = get_actors_use_case
