from __future__ import annotations

from mova.adapter.inbound.api.schemas.platform_admins_schema import PlatformAdminsSchema
from mova.app.dtos.platform_admins_dto import PlatformAdminsResponse
from mova.app.ports.input.platform_admins_use_case import PlatformAdminsUseCase


class PlatformAdminsInteractor(PlatformAdminsUseCase):
    async def introduce_myself(self, schemas: PlatformAdminsSchema) -> PlatformAdminsResponse:
        return PlatformAdminsResponse(id=schemas.id, name=schemas.name)
