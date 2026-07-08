"""태그 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.studio_tags_pg_repository import TagsPgRepository
from mova.app.ports.input.studio_tags_use_case import TagsUseCase
from mova.app.ports.output.studio_tags_repository import TagsRepositoryPort
from mova.app.use_cases.studio_tags_interactor import TagsInteractor


def get_tags_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> TagsRepositoryPort:
    return TagsPgRepository(session=db)


def get_tags_use_case(
    repository: TagsRepositoryPort = Depends(get_tags_repository),
) -> TagsUseCase:
    return TagsInteractor(repository=repository)


get_studio_tags_use_case = get_tags_use_case
