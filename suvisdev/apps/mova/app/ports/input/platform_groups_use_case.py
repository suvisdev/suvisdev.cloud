from __future__ import annotations

from abc import ABC, abstractmethod

from mova.adapter.inbound.api.schemas.platform_groups_schema import PlatformGroupsSchema
from mova.app.dtos.platform_groups_dto import PlatformGroupsResponse


class PlatformGroupsUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, schemas: PlatformGroupsSchema) -> PlatformGroupsResponse:
        pass
