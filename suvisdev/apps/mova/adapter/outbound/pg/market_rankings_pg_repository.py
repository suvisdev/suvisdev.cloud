"""랭킹 PgRepository — RankingsRepositoryPort 구현체."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_rankings_orm import MovaRanking
from mova.adapter.outbound.orm.market_user_actions_orm import (
    ACTION_BOOKING_INTENT,
    ACTION_CLICK,
    ACTION_EVAL_POSITIVE,
    MovaUserAction,
)
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
        latest_ranked_at = (
            select(func.max(MovaRanking.ranked_at))
            .where(MovaRanking.source == source)
            .scalar_subquery()
        )
        rows = (
            await self._session.execute(
                select(MovaRanking, MovaMovie, MovaChat)
                .join(MovaMovie, MovaRanking.movie_id == MovaMovie.id)
                .outerjoin(MovaChat, MovaRanking.chat_id == MovaChat.id)
                .where(MovaRanking.source == source, MovaRanking.ranked_at == latest_ranked_at)
                .order_by(MovaRanking.rank.asc())
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
                release_year=m.release_year or 0,
                rating=float(m.rating or 0),
                poster=m.poster_url or "",
                # movies.genres 제거(v2) — 랭킹 응답의 genres는 프론트가 소비하지 않아
                # (mova-api.ts 확인) tags 조인 없이 당장은 빈 리스트로 둔다.
                genres=[],
            )
            for r, m, c in rows
        ]
        logger.debug("[RankingsPgRepository] get_hot source=%s count=%d", source, len(items))
        return RankingListDto(items=items, source=source)

    async def aggregate_chat_trend(self, days: int, limit: int) -> list[ChatTrendAggRowDto]:
        """AI 검색 TOP 집계 — 2026-08-13: pick/hit(노출·응답) → user_actions.click.

        사용자가 채팅 결과 카드를 실제로 클릭한 경우만 신호로 카운트. 노출
        (picks) 신호는 완전히 제외 — "검색만 하고 순위에 반영되는 건 이상,
        클릭했을 때만 반영해야" 지침 반영.

        2026-08-28 확장: 채팅 3트랙 결정에 따라 예매 의지(booking_intent)와
        평가 후 긍정 반응(eval_positive)도 신호에 포함한다 — 단순 평가/예매
        질의 자체는 여전히 미집계(액션이 기록되지 않으므로 자연 배제).
        """
        since = datetime.now(UTC) - timedelta(days=days)
        click_count = func.count(MovaUserAction.id)

        rows = (
            await self._session.execute(
                select(
                    MovaUserAction.movie_id.label("movie_id"),
                    click_count.label("click_count"),
                )
                .where(
                    MovaUserAction.action_type.in_(
                        (ACTION_CLICK, ACTION_BOOKING_INTENT, ACTION_EVAL_POSITIVE)
                    )
                )
                .where(MovaUserAction.action_at >= since)
                .group_by(MovaUserAction.movie_id)
                .order_by(click_count.desc())
                .limit(limit)
            )
        ).all()

        result = [
            ChatTrendAggRowDto(
                movie_id=r.movie_id,
                click_count=int(r.click_count or 0),
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
