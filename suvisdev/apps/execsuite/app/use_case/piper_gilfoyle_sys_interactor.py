from __future__ import annotations

import logging

from execsuite.adapter.inbound.api.schemas.piper_gilfoyle_sys_schema import GilfoyleSysSchema
from execsuite.app.dtos.piper_gilfoyle_sys_dto import GilfoyleSysQuery, GilfoyleSysResponse
from execsuite.app.ports.input.piper_gilfoyle_sys_use_case import GilfoyleSysUseCase
from execsuite.app.ports.output.piper_gilfoyle_sys_port import GilfoyleSysPort

logger = logging.getLogger(__name__)


class GilfoyleSysInteractor(GilfoyleSysUseCase):
    def __init__(self, repository: GilfoyleSysPort) -> None:
        self._repository = repository

    async def introduce_myself(self, schemas: GilfoyleSysSchema) -> GilfoyleSysResponse:

        return await self._repository.introduce_myself(GilfoyleSysQuery(
            id=schemas.id,
            name=schemas.name,
        ))
