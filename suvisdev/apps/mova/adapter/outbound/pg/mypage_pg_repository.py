from __future__ import annotations

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_chat_orm import MovaChat
from mova.adapter.outbound.orm.market_picks_orm import MovaPick
from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
from mova.adapter.outbound.orm.market_user_actions_orm import ACTION_WATCHED, MovaUserAction
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.mypage_dto import (
    ActivitySummary,
    MypageDto,
    MyReviewItem,
    PickHistoryItem,
    SearchHistoryItem,
)
from mova.app.ports.output.mypage_repository import MypageRepository
from viewer.adapter.outbound.orm.user_orm import User

_MY_REVIEWS_LIMIT = 20


class MypagePgRepository(MypageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_mypage(self, user_id: int) -> MypageDto:
        profile_row = (
            await self._session.execute(
                select(User.nickname, User.preferred_genres).where(User.id == user_id)
            )
        ).one_or_none()
        nickname = profile_row.nickname if profile_row else None
        preferred_genres: list[str] = (
            list(profile_row.preferred_genres or []) if profile_row else []
        )

        picks_rows = (
            await self._session.execute(
                select(MovaPick, MovaMovie.slug, MovaMovie.poster_url)
                .join(MovaMovie, MovaMovie.id == MovaPick.movie_id)
                .where(MovaPick.user_id == user_id)
                .order_by(desc(MovaPick.batch_at))
                .limit(12)
            )
        ).all()
        recent_picks = [
            PickHistoryItem(
                pick_id=row.MovaPick.id,
                title=row.MovaPick.title_snapshot,
                hook=row.MovaPick.hook,
                slug=row.slug,
                poster_url=row.poster_url,
                batch_at=row.MovaPick.batch_at,
                feedback=row.MovaPick.feedback,
            )
            for row in picks_rows
        ]

        chat_rows = (
            await self._session.execute(
                select(MovaChat.refined_query, MovaChat.created_at)
                .where(MovaChat.user_id == user_id)
                .order_by(desc(MovaChat.last_used_at))
                .limit(10)
            )
        ).all()
        recent_searches = [
            SearchHistoryItem(refined_query=row.refined_query, searched_at=row.created_at)
            for row in chat_rows
        ]

        review_rows = (
            await self._session.execute(
                select(MovaReview, MovaMovie.title, MovaMovie.slug, MovaMovie.poster_url)
                .join(MovaMovie, MovaMovie.id == MovaReview.movie_id)
                .where(MovaReview.user_id == user_id)
                .order_by(desc(MovaReview.updated_at))
                .limit(_MY_REVIEWS_LIMIT)
            )
        ).all()
        my_reviews = [
            MyReviewItem(
                review_id=row.MovaReview.id,
                movie_id=row.MovaReview.movie_id,
                title=row.title,
                slug=row.slug,
                poster_url=row.poster_url,
                rating=row.MovaReview.rating,
                body=row.MovaReview.body,
                updated_at=row.MovaReview.updated_at,
                spoiler_spans=list(row.MovaReview.spoiler_spans or []),
            )
            for row in review_rows
        ]

        # user_actions는 행동 로그라 같은 영화가 여러 번 쌓인다(UNIQUE 없음) —
        # "본 영화 수"는 중복을 제거한 영화 수여야 한다.
        watched_count = int(
            (
                await self._session.execute(
                    select(func.count(distinct(MovaUserAction.movie_id))).where(
                        MovaUserAction.user_id == user_id,
                        MovaUserAction.action_type == ACTION_WATCHED,
                    )
                )
            ).scalar_one()
        )
        # 별점 없이 본문만 쓴 리뷰도 있으므로(2026-07-31) 개수는 전체,
        # 평균은 rating이 있는 것만 대상 — AVG는 NULL을 자동으로 제외한다.
        review_stats = (
            await self._session.execute(
                select(func.count(MovaReview.id), func.avg(MovaReview.rating)).where(
                    MovaReview.user_id == user_id
                )
            )
        ).one()
        average_rating = round(float(review_stats[1]), 2) if review_stats[1] is not None else None

        return MypageDto(
            nickname=nickname,
            preferred_genres=preferred_genres,
            recent_picks=recent_picks,
            recent_searches=recent_searches,
            my_reviews=my_reviews,
            activity=ActivitySummary(
                watched_count=watched_count,
                review_count=int(review_stats[0]),
                average_rating=average_rating,
            ),
        )
