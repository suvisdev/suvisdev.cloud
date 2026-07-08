"""영화↔배우 연결 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.studio_characters_pg_repository import CharactersPgRepository
from mova.app.ports.input.studio_characters_use_case import CharactersUseCase
from mova.app.ports.output.studio_characters_repository import CharactersRepositoryPort
from mova.app.use_cases.studio_characters_interactor import CharactersInteractor


def get_characters_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> CharactersRepositoryPort:
    return CharactersPgRepository(session=db)


def get_characters_use_case(
    repository: CharactersRepositoryPort = Depends(get_characters_repository),
) -> CharactersUseCase:
    return CharactersInteractor(repository=repository)


# 기존 stub 이름 호환
get_studio_characters_use_case = get_characters_use_case
