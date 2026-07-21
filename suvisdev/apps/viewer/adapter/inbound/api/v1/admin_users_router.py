"""관리자 전용 — 사용자 목록 API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from viewer.adapter.inbound.api.schemas.admin_users_schema import UserAdminSchema
from viewer.app.ports.input.admin_users_use_case import AdminUsersUseCase
from viewer.dependencies.admin_users_provider import get_admin_users_use_case
from viewer.dependencies.require_admin import AdminPrincipal, require_admin

admin_users_router = APIRouter(prefix="/admin/users", tags=["admin"])


@admin_users_router.get("", response_model=list[UserAdminSchema])
async def list_users(
    _: AdminPrincipal = Depends(require_admin),
    use_case: AdminUsersUseCase = Depends(get_admin_users_use_case),
) -> list[UserAdminSchema]:
    dtos = await use_case.list_users()
    return [dto.to_schema() for dto in dtos]
