from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.matrix.grid_oracle_database_manager import get_db
from dispatch.adapter.outbound.repositories.adress_repository import AdressRepository
from dispatch.app.ports.input.adress_use_case import AdressUseCase
from dispatch.app.ports.output.adress_port import AdressPort
from dispatch.app.use_cases.adress_interactor import AdressInteractor


def get_adress_repository(session: AsyncSession = Depends(get_db)) -> AdressPort:
    return AdressRepository(session=session)


def get_adress_use_case(
    repository: AdressPort = Depends(get_adress_repository),
) -> AdressUseCase:
    return AdressInteractor(repository=repository)
