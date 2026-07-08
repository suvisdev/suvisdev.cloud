from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from titanic.adapter.outbound.repositories.crew_walter_roaster_repository import WalterRepository
from titanic.app.ports.input.crew_walter_roaster_use_case import WalterUseCase
from titanic.app.ports.output.crew_walter_roaster_port import WalterPort
from titanic.app.use_cases.crew_walter_roaster_interactor import WalterInteractor


def get_walter_roaster_repository(
        db: AsyncSession = Depends(get_db)
) -> WalterPort:
    return WalterRepository(session=db)

def get_walter_roaster_use_case(
        repository: WalterPort = Depends(get_walter_roaster_repository)
) -> WalterUseCase:
    return WalterInteractor(repository=repository)
