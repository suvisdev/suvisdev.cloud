from __future__ import annotations

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gildle.adapter.outbound.orm.walk_orm import WalkOrm
from gildle.app.dtos.walk_dto import WalkListQuery, WalkStats, WalkSummary
from gildle.app.ports.output.walk_repository import WalkRepositoryPort
from gildle.domain.entities.walk_entity import Walk


def _to_domain(row: WalkOrm) -> Walk:
    return Walk(
        id=row.id,
        user_id=row.user_id,
        started_at=row.started_at,
        ended_at=row.ended_at,
        distance_m=row.distance_m,
        duration_s=row.duration_s,
        path=[[float(a), float(b)] for a, b in (row.path or [])],
        season_mode=row.season_mode,
        avg_shade_score=row.avg_shade_score,
        memo=row.memo,
    )


class WalkPgRepository(WalkRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, walk: Walk) -> Walk:
        row = WalkOrm(
            user_id=walk.user_id,
            started_at=walk.started_at,
            ended_at=walk.ended_at,
            distance_m=walk.distance_m,
            duration_s=walk.duration_s,
            path=walk.path,
            season_mode=walk.season_mode,
            avg_shade_score=walk.avg_shade_score,
            memo=walk.memo,
        )
        self._session.add(row)
        await self._session.flush()  # id 확보
        await self._session.commit()
        return _to_domain(row)

    async def list_by_user(self, query: WalkListQuery) -> list[WalkSummary]:
        rows = (
            await self._session.execute(
                select(
                    WalkOrm.id,
                    WalkOrm.started_at,
                    WalkOrm.ended_at,
                    WalkOrm.distance_m,
                    WalkOrm.duration_s,
                    WalkOrm.season_mode,
                    WalkOrm.avg_shade_score,
                )
                .where(WalkOrm.user_id == query.user_id)
                .order_by(WalkOrm.started_at.desc())
                .limit(query.limit)
                .offset(query.offset)
            )
        ).all()
        return [
            WalkSummary(
                id=r.id,
                started_at=r.started_at,
                ended_at=r.ended_at,
                distance_m=r.distance_m,
                duration_s=r.duration_s,
                season_mode=r.season_mode,
                avg_shade_score=r.avg_shade_score,
            )
            for r in rows
        ]

    async def get(self, walk_id: int) -> Walk | None:
        row = await self._session.get(WalkOrm, walk_id)
        return _to_domain(row) if row else None

    async def delete(self, walk_id: int) -> None:
        await self._session.execute(sa_delete(WalkOrm).where(WalkOrm.id == walk_id))
        await self._session.commit()

    async def delete_all_by_user(self, user_id: int) -> int:
        result = await self._session.execute(sa_delete(WalkOrm).where(WalkOrm.user_id == user_id))
        await self._session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def stats(self, user_id: int) -> WalkStats:
        row = (
            await self._session.execute(
                select(
                    func.count(WalkOrm.id),
                    func.coalesce(func.sum(WalkOrm.distance_m), 0),
                    func.coalesce(func.sum(WalkOrm.duration_s), 0),
                ).where(WalkOrm.user_id == user_id)
            )
        ).one()
        return WalkStats(
            total_count=row[0], total_distance_m=int(row[1]), total_duration_s=int(row[2])
        )
