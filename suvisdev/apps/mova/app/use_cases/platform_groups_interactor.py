from __future__ import annotations

from mova.adapter.inbound.api.schemas.platform_groups_schema import PlatformGroupsSchema
from mova.app.dtos.platform_groups_dto import PlatformGroupsResponse
from mova.app.ports.input.platform_groups_use_case import PlatformGroupsUseCase


class PlatformGroupsInteractor(PlatformGroupsUseCase):
    async def introduce_myself(self, schemas: PlatformGroupsSchema) -> PlatformGroupsResponse:
        return PlatformGroupsResponse(id=schemas.id, name=schemas.name)
