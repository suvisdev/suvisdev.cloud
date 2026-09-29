from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytics.adapter.outbound.orm.visitor_activity_orm import VisitorActivityOrm
from analytics.app.dtos.visitor_summary_dto import DailyVisitorCountDto
from analytics.app.ports.output.visitor_activity_repository import VisitorActivityRepository


class VisitorActivityPgRepository(VisitorActivityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_visit(
        self,
        visitor_id: str,
        visit_date: date,
        now: datetime,
        *,
        is_bot: bool = False,
        user_agent: str | None = None,
    ) -> None:
        stmt = insert(VisitorActivityOrm).values(
            visitor_id=visitor_id,
            visit_date=visit_date,
            first_seen_at=now,
            last_seen_at=now,
            is_bot=is_bot,
            user_agent=user_agent,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[VisitorActivityOrm.visitor_id, VisitorActivityOrm.visit_date],
            set_={"last_seen_at": now},
        )
        await self._session.execute(stmt)

    async def count_active_since(self, since: datetime) -> int:
        stmt = select(func.count(func.distinct(VisitorActivityOrm.visitor_id))).where(
            VisitorActivityOrm.last_seen_at >= since, VisitorActivityOrm.is_bot.is_(False)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_unique_on(self, visit_date: date) -> int:
        stmt = select(func.count(func.distinct(VisitorActivityOrm.visitor_id))).where(
            VisitorActivityOrm.visit_date == visit_date, VisitorActivityOrm.is_bot.is_(False)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_bots_on(self, visit_date: date) -> int:
        stmt = select(func.count(func.distinct(VisitorActivityOrm.visitor_id))).where(
            VisitorActivityOrm.visit_date == visit_date, VisitorActivityOrm.is_bot.is_(True)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_one_shot_on(self, visit_date: date) -> int:
        stmt = select(func.count(func.distinct(VisitorActivityOrm.visitor_id))).where(
            VisitorActivityOrm.visit_date == visit_date,
            VisitorActivityOrm.is_bot.is_(False),
            VisitorActivityOrm.first_seen_at == VisitorActivityOrm.last_seen_at,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def daily_counts_since(self, start_date: date) -> list[DailyVisitorCountDto]:
        vid = VisitorActivityOrm.visitor_id
        human = VisitorActivityOrm.is_bot.is_(False)
        stmt = (
            select(
                VisitorActivityOrm.visit_date,
                func.count(func.distinct(vid)).filter(human),
                func.count(func.distinct(vid)).filter(VisitorActivityOrm.is_bot.is_(True)),
                func.count(func.distinct(vid)).filter(
                    human, VisitorActivityOrm.first_seen_at == VisitorActivityOrm.last_seen_at
                ),
            )
            .where(VisitorActivityOrm.visit_date >= start_date)
            .group_by(VisitorActivityOrm.visit_date)
            .order_by(VisitorActivityOrm.visit_date)
        )
        result = await self._session.execute(stmt)
        return [
            DailyVisitorCountDto(date=row[0], count=row[1], bots=row[2], one_shot=row[3])
            for row in result.all()
        ]

    async def count_unique_total(self) -> int:
        stmt = select(func.count(func.distinct(VisitorActivityOrm.visitor_id))).where(
            VisitorActivityOrm.is_bot.is_(False)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
