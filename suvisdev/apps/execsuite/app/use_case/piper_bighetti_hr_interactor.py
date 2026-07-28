from __future__ import annotations

import logging

from execsuite.adapter.inbound.api.schemas.piper_bighetti_hr_schema import BighettiHrSchema
from execsuite.app.dtos.piper_bighetti_hr_dto import BighettiHrQuery, BighettiHrResponse
from execsuite.app.ports.input.piper_bighetti_hr_use_case import BighettiHrUseCase
from execsuite.app.ports.output.piper_bighetti_hr_port import BighettiHrPort

logger = logging.getLogger(__name__)


class BighettiHrInteractor(BighettiHrUseCase):
    def __init__(self, repository: BighettiHrPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: BighettiHrSchema) -> BighettiHrResponse:

        return await self._repository.introduce_myself(BighettiHrQuery(
            id=schemas.id,
            name=schemas.name,
        ))
