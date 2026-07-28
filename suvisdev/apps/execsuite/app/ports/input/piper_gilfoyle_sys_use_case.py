from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.adapter.inbound.api.schemas.piper_gilfoyle_sys_schema import GilfoyleSysSchema
from execsuite.app.dtos.piper_gilfoyle_sys_dto import GilfoyleSysResponse


class GilfoyleSysUseCase(ABC):
    """piper_gilfoyle_sys input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: GilfoyleSysSchema)->GilfoyleSysResponse:
        pass
