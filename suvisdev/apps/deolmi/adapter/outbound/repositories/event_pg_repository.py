from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deolmi.adapter.outbound.orm.event_orm import DeolmiEventOrm
from deolmi.adapter.outbound.orm.site_orm import DeolmiSiteOrm
from deolmi.app.dtos.score_dto import ScoreResultDto
from deolmi.app.dtos.site_dto import EventSummaryDto
from deolmi.app.ports.output.event_repository import EventRepositoryPort


class EventPgRepository(EventRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, site_id: int, ip: str, signals: dict[str, float], result: ScoreResultDto
    ) -> None:
        self._session.add(
            DeolmiEventOrm(
                site_id=site_id,
                ip=ip,
                score=result.score,
                verdict=result.verdict,
                rule_score=result.rule_score,
                model_score=result.model_score,
                decided_by=result.decided_by,
                signals=signals,
                reasons=result.reasons,
            )
        )
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def count(self) -> int:
        return int(
            (await self._session.execute(select(func.count(DeolmiEventOrm.id)))).scalar_one()
        )

    async def recent(self, n: int) -> list[EventSummaryDto]:
        rows = await self._session.execute(
            select(DeolmiEventOrm, DeolmiSiteOrm.site_key)
            .join(DeolmiSiteOrm, DeolmiSiteOrm.id == DeolmiEventOrm.site_id)
            .order_by(DeolmiEventOrm.id.desc())
            .limit(n)
        )
        return [
            EventSummaryDto(
                created_at=e.created_at,
                site_key=site_key,
                ip=e.ip,
                score=e.score,
                verdict=e.verdict,
                decided_by=e.decided_by,
            )
            for e, site_key in rows.all()
        ]

    async def signals_by_verdict(self, verdict: str, limit: int) -> list[dict[str, Any]]:
        rows = await self._session.execute(
            select(DeolmiEventOrm.signals)
            .where(DeolmiEventOrm.verdict == verdict)
            .order_by(DeolmiEventOrm.id.desc())
            .limit(limit)
        )
        return list(rows.scalars())
