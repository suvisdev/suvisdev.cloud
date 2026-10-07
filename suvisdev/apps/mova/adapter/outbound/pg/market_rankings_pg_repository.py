"""랭킹 PgRepository — RankingsRepositoryPort 구현체."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_movie_views_orm import MovaMovieView
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
_KST = ZoneInfo("Asia/Seoul")


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

    def _view_counts(self, days: int, limit: int) -> Select[tuple[int, int]]:
        """최근 days일(KST 날짜 기준, 오늘 포함) 열람 수 상위 — (movie_id, views)."""
        since = datetime.now(UTC).astimezone(_KST).date() - timedelta(days=days - 1)
        views = func.count(MovaMovieView.id)
        return (
            select(MovaMovieView.movie_id.label("movie_id"), views.label("views"))
            .where(MovaMovieView.view_date >= since)
            .group_by(MovaMovieView.movie_id)
            # 동점이면 최근에 열린 영화가 위
            .order_by(views.desc(), func.max(MovaMovieView.viewed_at).desc())
            .limit(limit)
        )

    async def aggregate_chat_trend(self, days: int, limit: int) -> list[ChatTrendAggRowDto]:
        """mova 랭킹 집계 — 2026-10-07: 채팅 카드 클릭(user_actions) → 영화 상세 열람(movie_views).

        사용자 결정 "많이 클릭한 영화를 순위별로, 비로그인 열람까지". 어디서 들어오든(채팅 카드·목록·검색·랭킹)
        상세를 연 것을 사람·영화·하루 1회로 센다. 예매 의지·평가 후 긍정 반응은 "클릭"이 아니라 뺐다.
        """
        rows = (await self._session.execute(self._view_counts(days, limit))).all()
        result = [
            ChatTrendAggRowDto(movie_id=r.movie_id, click_count=int(r.views or 0)) for r in rows
        ]
        logger.debug(
            "[RankingsPgRepository] aggregate_chat_trend days=%d count=%d", days, len(result)
        )
        return result

    async def get_view_ranking(self, days: int, limit: int) -> RankingListDto:
        counts = self._view_counts(days, limit).subquery()
        rows = (
            await self._session.execute(
                select(MovaMovie, counts.c.views)
                .join(counts, counts.c.movie_id == MovaMovie.id)
                .order_by(counts.c.views.desc(), MovaMovie.id.asc())
            )
        ).all()
        today = datetime.now(UTC).astimezone(_KST).date()
        items = [
            RankingItemDto(
                id=m.id,
                rank=rank,
                movie_id=m.id,
                chat_id=None,
                source=RANKING_SOURCE_CHAT_TREND,
                score=int(views),
                badge=None,
                ranked_at=today,
                refined_query=None,
                slug=m.slug,
                title=m.title,
                release_year=m.release_year or 0,
                rating=float(m.rating or 0),
                poster=m.poster_url or "",
                genres=[],
            )
            for rank, (m, views) in enumerate(rows, start=1)
        ]
        return RankingListDto(items=items, source=RANKING_SOURCE_CHAT_TREND)

    async def record_view(self, movie_id: int, viewer_key: str, view_date: date) -> bool:
        try:
            await self._session.execute(
                insert(MovaMovieView)
                .values(movie_id=movie_id, viewer_key=viewer_key, view_date=view_date)
                .on_conflict_do_nothing(constraint="uq_movie_views_daily")
            )
            await self._session.commit()
        except IntegrityError:  # 없는 movie_id(FK) — 공개 엔드포인트라 조용히 무시
            await self._session.rollback()
            return False
        return True

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
