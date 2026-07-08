from __future__ import annotations

from mova.adapter.inbound.api.schemas.platform_users_schema import PlatformUsersSchema
from mova.app.dtos.platform_users_dto import PlatformUsersResponse
from mova.app.ports.input.platform_users_use_case import PlatformUsersUseCase


class PlatformUsersInteractor(PlatformUsersUseCase):
    async def introduce_myself(self, schemas: PlatformUsersSchema) -> PlatformUsersResponse:
        return PlatformUsersResponse(id=schemas.id, name=schemas.name)
