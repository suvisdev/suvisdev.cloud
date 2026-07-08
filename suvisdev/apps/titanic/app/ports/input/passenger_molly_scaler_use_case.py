from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.adapter.inbound.api.schemas.passenger_molly_scaler_schema import MollyScalerSchema
from titanic.app.dtos.passenger_molly_scaler_dto import MollyScalerResponse


class MollyScalerUseCase(ABC):
    """molly_scaler input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: MollyScalerSchema)->MollyScalerResponse:
        pass
