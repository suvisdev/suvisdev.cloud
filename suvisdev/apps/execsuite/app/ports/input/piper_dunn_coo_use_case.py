from __future__ import annotations

from abc import ABC, abstractmethod

from execsuite.adapter.inbound.api.schemas.piper_dunn_coo_schema import DunnCooSchema
from execsuite.app.dtos.piper_dunn_coo_dto import DunnCooResponse


class DunnCooUseCase(ABC):
    """piper_dunn_coo input port."""

    @abstractmethod
    async def introduce_myself(self, schemas: DunnCooSchema)->DunnCooResponse:
        pass
