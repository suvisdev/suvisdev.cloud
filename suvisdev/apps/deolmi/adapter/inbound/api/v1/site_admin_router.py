"""운영자 전용 — 고객 키 발급·목록·통계. 전부 require_admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from shared.security.require_admin import AdminPrincipal, require_admin

from deolmi.adapter.inbound.api.schemas.site_schema import (
    SiteCreateSchema,
    SiteIssuedSchema,
    SiteSchema,
    StatsSchema,
)
from deolmi.app.dtos.site_dto import SiteCreateCommand
from deolmi.app.ports.input.site_admin_use_case import SiteAdminUseCase
from deolmi.dependencies.deolmi_provider import get_site_admin_use_case

site_admin_router = APIRouter(prefix="/admin", tags=["deolmi-admin"])


@site_admin_router.post(
    "/sites", response_model=SiteIssuedSchema, status_code=status.HTTP_201_CREATED
)
async def create_site(
    req: SiteCreateSchema,
    _: AdminPrincipal = Depends(require_admin),
    use_case: SiteAdminUseCase = Depends(get_site_admin_use_case),
) -> SiteIssuedSchema:
    return (await use_case.create_site(SiteCreateCommand.from_schema(req))).to_schema()


@site_admin_router.get("/sites", response_model=list[SiteSchema])
async def list_sites(
    _: AdminPrincipal = Depends(require_admin),
    use_case: SiteAdminUseCase = Depends(get_site_admin_use_case),
) -> list[SiteSchema]:
    return [s.to_schema() for s in await use_case.list_sites()]


@site_admin_router.get("/stats", response_model=StatsSchema)
async def stats(
    _: AdminPrincipal = Depends(require_admin),
    use_case: SiteAdminUseCase = Depends(get_site_admin_use_case),
) -> StatsSchema:
    return (await use_case.stats()).to_schema()
