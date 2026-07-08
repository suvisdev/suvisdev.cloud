"""어시스턴트 DI."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_mova_db
from mova.adapter.outbound.pg.platform_assistants_pg_repository import AssistantsPgRepository
from mova.app.ports.input.platform_assistants_use_case import AssistantsUseCase
from mova.app.ports.output.platform_assistants_repository import AssistantsRepositoryPort
from mova.app.use_cases.platform_assistants_interactor import AssistantsInteractor


def get_assistants_repository(
    db: AsyncSession = Depends(get_mova_db),
) -> AssistantsRepositoryPort:
    return AssistantsPgRepository(session=db)


def get_assistants_use_case(
    repository: AssistantsRepositoryPort = Depends(get_assistants_repository),
) -> AssistantsUseCase:
    return AssistantsInteractor(repository=repository)


get_platform_assistants_use_case = get_assistants_use_case
