from __future__ import annotations

import logging

from execsuite.adapter.inbound.api.schemas.piper_hendricks_ceo_schema import HendricksCeoSchema
from execsuite.app.dtos.piper_hendricks_ceo_dto import HendricksCeoQuery, HendricksCeoResponse
from execsuite.app.ports.input.piper_hendricks_ceo_use_case import HendricksCeoUseCase
from execsuite.app.ports.output.piper_hendricks_ceo_port import HendricksCeoPort

logger = logging.getLogger(__name__)


class HendricksCeoInteractor(HendricksCeoUseCase):
    def __init__(self, repository: HendricksCeoPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: HendricksCeoSchema) -> HendricksCeoResponse:

        return await self._repository.introduce_myself(HendricksCeoQuery(
            id=schemas.id,
            name=schemas.name,
        ))
