from __future__ import annotations

import logging

from titanic.adapter.inbound.api.schemas.passenger_isidor_couple_schema import IsidorCoupleSchema
from titanic.app.dtos.passenger_isidor_couple_dto import IsidorCoupleQuery, IsidorCoupleResponse
from titanic.app.ports.input.passenger_isidor_couple_use_case import IsidorCoupleUseCase
from titanic.app.ports.output.passenger_isidor_couple_port import IsidorCouplePort

logger = logging.getLogger(__name__)


class IsidorCoupleInteractor(IsidorCoupleUseCase):
    def __init__(self, repository: IsidorCouplePort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: IsidorCoupleSchema) -> IsidorCoupleResponse:
    
        return await self._repository.introduce_myself(IsidorCoupleQuery(
            id=schemas.id,
            name=schemas.name,
        ))
