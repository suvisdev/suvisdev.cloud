from __future__ import annotations

import logging

from execsuite.adapter.inbound.api.schemas.piper_dinesh_dash_schema import DineshDashSchema
from execsuite.app.dtos.piper_dinesh_dash_dto import DineshDashQuery, DineshDashResponse
from execsuite.app.ports.input.piper_dinesh_dash_use_case import DineshDashUseCase
from execsuite.app.ports.output.piper_dinesh_dash_port import DineshDashPort

logger = logging.getLogger(__name__)


class DineshDashInteractor(DineshDashUseCase):
    def __init__(self, repository: DineshDashPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: DineshDashSchema) -> DineshDashResponse:

        return await self._repository.introduce_myself(DineshDashQuery(
            id=schemas.id,
            name=schemas.name,
        ))
