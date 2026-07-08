from __future__ import annotations

from abc import ABC, abstractmethod

from mova.adapter.inbound.api.schemas.platform_admins_schema import PlatformAdminsSchema
from mova.app.dtos.platform_admins_dto import PlatformAdminsResponse


class PlatformAdminsUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, schemas: PlatformAdminsSchema) -> PlatformAdminsResponse:
        pass
