from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deolmi.adapter.outbound.orm.site_orm import DeolmiSiteOrm
from deolmi.app.dtos.site_dto import SiteCreateCommand, SiteDto
from deolmi.app.ports.output.site_repository import SiteRepositoryPort


class SitePgRepository(SiteRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, site_key: str) -> SiteDto | None:
        row = (
            await self._session.execute(
                select(DeolmiSiteOrm).where(
                    DeolmiSiteOrm.site_key == site_key, DeolmiSiteOrm.active.is_(True)
                )
            )
        ).scalar_one_or_none()
        return SiteDto.from_orm(row) if row else None

    async def create(self, command: SiteCreateCommand, site_key: str, secret_hash: str) -> SiteDto:
        row = DeolmiSiteOrm(
            site_key=site_key,
            secret_hash=secret_hash,
            name=command.name,
            plan=command.plan,
            domains=",".join(command.domains),
            active=True,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return SiteDto.from_orm(row)

    async def list_all(self) -> list[SiteDto]:
        rows = (
            await self._session.execute(select(DeolmiSiteOrm).order_by(DeolmiSiteOrm.id))
        ).scalars()
        return [SiteDto.from_orm(r) for r in rows]
