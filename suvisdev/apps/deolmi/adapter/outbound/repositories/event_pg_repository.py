from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deolmi.adapter.outbound.orm.event_orm import DeolmiEventOrm
from deolmi.adapter.outbound.orm.site_orm import DeolmiSiteOrm
from deolmi.app.dtos.score_dto import ScoreResultDto
from deolmi.app.dtos.site_dto import EventSummaryDto
from deolmi.app.ports.output.event_repository import EventLogPort, EventRepositoryPort


class EventPgLogWriter(EventLogPort):
    """응답을 보낸 뒤(BackgroundTasks) 로그를 쓴다. 그때는 요청 세션이 이미 닫혔을 수 있어
    쓸 때마다 세션을 새로 뽑는다 — mova review_embedding_backfill과 같은 방식."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(
        self, site_id: int, ip: str, signals: dict[str, float], result: ScoreResultDto
    ) -> None:
        async with self._session_factory() as session:
            await EventPgRepository(session).add(site_id, ip, signals, result)


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
