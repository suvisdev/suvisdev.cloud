from __future__ import annotations

from abc import ABC, abstractmethod

from mova.adapter.inbound.api.schemas.platform_users_schema import PlatformUsersSchema
from mova.app.dtos.platform_users_dto import PlatformUsersResponse


class PlatformUsersUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, schemas: PlatformUsersSchema) -> PlatformUsersResponse:
        pass
