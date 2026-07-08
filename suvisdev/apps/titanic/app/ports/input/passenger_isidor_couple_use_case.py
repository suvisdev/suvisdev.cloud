from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.passenger_isidor_couple_schema import IsidorCoupleSchema
from titanic.app.dtos.passenger_isidor_couple_dto import IsidorCoupleResponse


class IsidorCoupleUseCase(ABC):
    """isidor_couple input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: IsidorCoupleSchema)->IsidorCoupleResponse:
        pass
