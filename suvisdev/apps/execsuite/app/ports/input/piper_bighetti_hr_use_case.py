from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.adapter.inbound.api.schemas.piper_bighetti_hr_schema import BighettiHrSchema
from execsuite.app.dtos.piper_bighetti_hr_dto import BighettiHrResponse


class BighettiHrUseCase(ABC):
    """piper_bighetti_hr input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: BighettiHrSchema)->BighettiHrResponse:
        pass
