from __future__ import annotations

from abc import ABC, abstractmethod

from silicon_valley.adapter.inbound.api.schemas.piper_hendricks_ceo_schema import HendricksCeoSchema
from silicon_valley.app.dtos.piper_hendricks_ceo_dto import HendricksCeoResponse


class HendricksCeoUseCase(ABC):
    """piper_hendricks_ceo input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: HendricksCeoSchema)->HendricksCeoResponse:
        pass
