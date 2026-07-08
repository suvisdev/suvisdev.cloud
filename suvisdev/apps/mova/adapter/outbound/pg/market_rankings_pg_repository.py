"""랭킹 PgRepository — RankingsRepositoryPort 구현체."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.market_rankings_orm import MovaRanking
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_rankings_dto import (
    ChatTrendAggRowDto,
    ChatTrendRankingRowDto,
    RankingItemDto,
    RankingListDto,
)
from mova.app.ports.output.market_rankings_repository import RankingsRepositoryPort
from mova.domain.value_objects.market_rankings_vo import (
    RANKING_SOURCE_BOX_OFFICE,
    RANKING_SOURCE_CHAT_TREND,
)

logger = logging.getLogger(__name__)


class RankingsPgRepository(RankingsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_hot(self, source: str, limit: int) -> RankingListDto:
        rows = (
            await self._session.execute(
                select(MovaRanking, MovaMovie, MovaChat)
                .join(MovaMovie, MovaRanking.movie_id == MovaMovie.id)
                .outerjoin(MovaChat, MovaRanking.chat_id == MovaChat.id)
                .where(MovaRanking.source == source)
                .order_by(MovaRanking.ranked_at.desc(), MovaRanking.rank.asc())
                .limit(limit)
            )
        ).all()

        items = [
            RankingItemDto(
                id=r.id,
                rank=r.rank,
                movie_id=r.movie_id,
                chat_id=r.chat_id,
                source=r.source,
                score=r.score,
                badge=r.badge,
                ranked_at=r.ranked_at,
                refined_query=c.refined_query if c else None,
                slug=m.slug,
                title=m.title,
                release_year=m.release_year or "",
                rating=float(m.rating or 0),
                poster=m.poster_url or "",
                genres=list(m.genres or []),
            )
            for r, m, c in rows
        ]
        logger.debug("[RankingsPgRepository] get_hot source=%s count=%d", source, len(items))
        return RankingListDto(items=items, source=source)

    async def aggregate_chat_trend(self, days: int, limit: int) -> list[ChatTrendAggRowDto]:
        since = datetime.now(UTC) - timedelta(days=days)
        pick_count = func.count(MovaPick.id)
        hit_sum = func.coalesce(func.sum(MovaChat.hit_count), 0)

        rows = (
            await self._session.execute(
                select(
                    MovaPick.movie_id.label("movie_id"),
                    pick_count.label("pick_count"),
                    hit_sum.label("hit_sum"),
                )
                .join(MovaChat, MovaPick.chat_id == MovaChat.id)
                .where(MovaPick.batch_at >= since)
                .group_by(MovaPick.movie_id)
                .order_by((pick_count + hit_sum).desc())
                .limit(limit)
            )
        ).all()

        result = [
            ChatTrendAggRowDto(
                movie_id=r.movie_id,
                pick_count=int(r.pick_count or 0),
                hit_sum=int(r.hit_sum or 0),
            )
            for r in rows
        ]
        logger.debug(
            "[RankingsPgRepository] aggregate_chat_trend days=%d count=%d", days, len(result)
        )
        return result

    async def save_chat_trend_ranking(
        self,
        rows: list[ChatTrendRankingRowDto],
        ranked_at: date,
    ) -> int:
        # 동일 일자·source 스냅샷 덮어쓰기 — UNIQUE(rank, ranked_at, source) 충돌 방지.
        await self._session.execute(
            delete(MovaRanking).where(
                MovaRanking.source == RANKING_SOURCE_CHAT_TREND,
                MovaRanking.ranked_at == ranked_at,
            )
        )
        for row in rows:
            self._session.add(
                MovaRanking(
                    rank=row.rank,
                    movie_id=row.movie_id,
                    chat_id=row.chat_id,
                    source=RANKING_SOURCE_CHAT_TREND,
                    score=row.score,
                    badge=row.badge,
                    ranked_at=ranked_at,
                )
            )
        await self._session.commit()
        logger.debug(
            "[RankingsPgRepository] save_chat_trend_ranking ranked_at=%s count=%d",
            ranked_at,
            len(rows),
        )
        return len(rows)

    async def save_box_office_ranking(self, movie_ids: list[int], ranked_at: date) -> int:
        if not movie_ids:
            return 0
        await self._session.execute(
            delete(MovaRanking).where(
                MovaRanking.source == RANKING_SOURCE_BOX_OFFICE,
                MovaRanking.ranked_at == ranked_at,
            )
        )
        for rank, movie_id in enumerate(movie_ids, start=1):
            self._session.add(
                MovaRanking(
                    rank=rank,
                    movie_id=movie_id,
                    chat_id=None,
                    source=RANKING_SOURCE_BOX_OFFICE,
                    score=None,
                    badge=None,
                    ranked_at=ranked_at,
                )
            )
        await self._session.commit()
        logger.debug(
            "[RankingsPgRepository] save_box_office_ranking ranked_at=%s count=%d",
            ranked_at,
            len(movie_ids),
        )
        return len(movie_ids)
