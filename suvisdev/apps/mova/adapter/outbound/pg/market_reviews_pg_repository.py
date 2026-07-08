"""리뷰 PgRepository — ReviewsRepositoryPort 구현체."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_reviews_orm import (
    ACTION_REVIEW,
    EVENT_ACTION_TYPES,
    MovaReview,
)
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewDto,
    ReviewWithUserDto,
)
from mova.app.ports.output.market_reviews_repository import ReviewsRepositoryPort
from viewer.adapter.outbound.orm.user_orm import User

logger = logging.getLogger(__name__)


class ReviewsPgRepository(ReviewsRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        if action_type not in EVENT_ACTION_TYPES:
            action_type = "click"
        row = MovaReview(
            user_id=user_id,
            movie_id=movie_id,
            action_type=action_type,
            rating=None,
            body=None,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        return ReviewActivityDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            action_type=row.action_type,
            action_at=row.action_at,
        )

    async def add_review(self, user_id: int, movie_id: int, rating: float, body: str) -> ReviewDto:
        row = MovaReview(
            user_id=user_id,
            movie_id=movie_id,
            action_type=ACTION_REVIEW,
            rating=max(1.0, min(5.0, float(rating))),
            body=body,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        await self._update_movie_rating(movie_id)
        return ReviewDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            rating=float(row.rating or 0),
            body=row.body or "",
            action_at=row.action_at,
        )

    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        rows = (
            await self._session.execute(
                select(MovaReview, User.nickname)
                .join(User, MovaReview.user_id == User.id)
                .where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.action_type == ACTION_REVIEW,
                )
                .order_by(MovaReview.action_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [
            ReviewWithUserDto(
                id=r.id,
                user_id=r.user_id,
                nickname=nickname or "",
                movie_id=r.movie_id,
                rating=float(r.rating or 0),
                body=r.body or "",
                created_at=r.action_at,
            )
            for r, nickname in rows
        ]

    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        row = (
            await self._session.execute(
                select(MovaReview).where(
                    MovaReview.id == review_id,
                    MovaReview.action_type == ACTION_REVIEW,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        if rating is not None:
            row.rating = max(1.0, min(5.0, float(rating)))
        if body is not None:
            row.body = body
        await self._session.commit()
        await self._update_movie_rating(row.movie_id)
        return ReviewDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            rating=float(row.rating or 0),
            body=row.body or "",
            action_at=row.action_at,
        )

    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        result = (
            await self._session.execute(
                select(
                    func.avg(MovaReview.rating).label("avg"),
                    func.count(MovaReview.id).label("cnt"),
                ).where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.action_type == ACTION_REVIEW,
                    MovaReview.rating.isnot(None),
                )
            )
        ).one()
        return MovieRatingSummaryDto(
            movie_id=movie_id,
            average_rating=round(float(result.avg or 0), 2),
            review_count=int(result.cnt or 0),
        )

    async def _update_movie_rating(self, movie_id: int) -> None:
        """reviews upsert 후 movies.rating 갱신."""
        result = (
            await self._session.execute(
                select(func.avg(MovaReview.rating)).where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.action_type == ACTION_REVIEW,
                    MovaReview.rating.isnot(None),
                )
            )
        ).scalar_one_or_none()
        if result is None:
            return
        movie = (
            await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        ).scalar_one_or_none()
        if movie:
            movie.rating = round(float(result), 2)
            await self._session.commit()
