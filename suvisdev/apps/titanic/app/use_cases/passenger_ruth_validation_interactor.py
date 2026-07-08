from __future__ import annotations

import logging

from titanic.adapter.inbound.api.schemas.passenger_ruth_validation_schema import (
    RuthValidationSchema,
)
from titanic.app.dtos.passenger_ruth_validation_dto import (
    RuthValidationQuery,
    RuthValidationResponse,
)
from titanic.app.ports.input.passenger_ruth_validation_use_case import RuthValidationUseCase
from titanic.app.ports.output.passenger_ruth_validation_port import RuthValidationPort

logger = logging.getLogger(__name__)


class RuthValidationInteractor(RuthValidationUseCase):
    def __init__(self, repository: RuthValidationPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: RuthValidationSchema) -> RuthValidationResponse:
       
       
         return await self._repository.introduce_myself(RuthValidationQuery(
            id=schemas.id,
            name=schemas.name,
        ))
      
