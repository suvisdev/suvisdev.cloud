from __future__ import annotations

import logging

from titanic.adapter.inbound.api.schemas.passenger_molly_scaler_schema import MollyScalerSchema
from titanic.app.dtos.passenger_molly_scaler_dto import MollyScalerQuery, MollyScalerResponse
from titanic.app.ports.input.passenger_molly_scaler_use_case import MollyScalerUseCase
from titanic.app.ports.output.passenger_molly_scaler_port import MollyScalerPort

logger = logging.getLogger(__name__)


class MollyScalerInteractor(MollyScalerUseCase):
    def __init__(self, repository: MollyScalerPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: MollyScalerSchema) -> MollyScalerResponse:
     
        return await self._repository.introduce_myself(MollyScalerQuery(
            id=schemas.id,
            name=schemas.name,
        ))
