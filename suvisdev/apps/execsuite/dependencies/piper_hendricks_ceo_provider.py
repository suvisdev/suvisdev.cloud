from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from execsuite.adapter.outbound.repositories.piper_hendricks_ceo_repository import (
    HendricksCeoRepository,
)
from execsuite.app.ports.input.piper_hendricks_ceo_use_case import HendricksCeoUseCase
from execsuite.app.ports.output.piper_hendricks_ceo_port import HendricksCeoPort
from execsuite.app.use_case.piper_hendricks_ceo_interactor import HendricksCeoInteractor


def get_hendricks_ceo_repository(db: AsyncSession = Depends(get_db)) -> HendricksCeoPort:
    return HendricksCeoRepository(session=db)


def get_hendricks_ceo_use_case(
    repository: HendricksCeoPort = Depends(get_hendricks_ceo_repository),
) -> HendricksCeoUseCase:
    return HendricksCeoInteractor(repository=repository)
