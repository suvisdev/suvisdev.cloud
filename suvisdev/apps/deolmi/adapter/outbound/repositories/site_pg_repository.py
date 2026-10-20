from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deolmi.adapter.outbound.orm.site_orm import DeolmiSiteOrm
from deolmi.app.dtos.site_dto import SiteCreateCommand, SiteDto
from deolmi.app.ports.output.site_repository import SiteLookupPort, SiteRepositoryPort


class SitePgLookup(SiteLookupPort):
    """채점 경로의 키 조회 — 조회 동안만 연결을 빌리고 바로 돌려준다.

    요청 세션(get_db)을 쓰면 연결을 응답 뒤 로그 기록(BackgroundTasks)이 끝날 때까지 쥐고 있고,
    그 로그가 같은 풀에서 연결을 하나 더 기다린다 — 동시 요청이 풀을 채우면 서로 막힌다(10-20 리뷰, 풀 1개 E2E 재현).
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_active(self, site_key: str) -> SiteDto | None:
        async with self._session_factory() as session:
            return await SitePgRepository(session).get_active(site_key)


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
