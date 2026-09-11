"""리뷰 PgRepository — ReviewsRepositoryPort 구현체."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mova.adapter.outbound.orm.market_review_comments_orm import MovaReviewComment
from mova.adapter.outbound.orm.market_review_votes_orm import MovaReviewVote
from mova.adapter.outbound.orm.market_reviews_orm import MovaReview
from mova.adapter.outbound.orm.market_user_actions_orm import (
    ACTION_WATCHED,
    EVENT_ACTION_TYPES,
    MovaUserAction,
)
from mova.adapter.outbound.orm.studio_movies_orm import MovaMovie
from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewCommentDto,
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
        row = MovaUserAction(
            user_id=user_id,
            movie_id=movie_id,
            action_type=action_type,
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

    async def has_watched(self, user_id: int, movie_id: int) -> bool:
        row = (
            await self._session.execute(
                select(MovaUserAction.id)
                .where(
                    MovaUserAction.user_id == user_id,
                    MovaUserAction.movie_id == movie_id,
                    MovaUserAction.action_type == ACTION_WATCHED,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return row is not None

    async def add_review(
        self, user_id: int, movie_id: int, rating: float | None, body: str | None
    ) -> ReviewDto:
        row = MovaReview(
            user_id=user_id,
            movie_id=movie_id,
            rating=max(0.5, min(5.0, float(rating))) if rating is not None else None,
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
            action_at=row.created_at,
            spoiler_spans=list(row.spoiler_spans or []),
        )

    async def find_by_user_and_movie(self, user_id: int, movie_id: int) -> ReviewDto | None:
        row = (
            await self._session.execute(
                select(MovaReview).where(
                    MovaReview.user_id == user_id,
                    MovaReview.movie_id == movie_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return ReviewDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            rating=float(row.rating or 0),
            body=row.body or "",
            action_at=row.created_at,
            spoiler_spans=list(row.spoiler_spans or []),
        )

    async def get_by_id(self, review_id: int) -> ReviewDto | None:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return None
        return ReviewDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            rating=float(row.rating or 0),
            body=row.body or "",
            action_at=row.created_at,
            spoiler_spans=list(row.spoiler_spans or []),
        )

    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        vote_count_sub = (
            select(func.count(MovaReviewVote.id))
            .where(MovaReviewVote.review_id == MovaReview.id)
            .correlate(MovaReview)
            .scalar_subquery()
            .label("vote_count")
        )
        rows = (
            await self._session.execute(
                select(MovaReview, User.nickname, vote_count_sub)
                .join(User, MovaReview.user_id == User.id)
                .where(MovaReview.movie_id == movie_id)
                .order_by(MovaReview.created_at.desc())
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
                created_at=r.created_at,
                spoiler_spans=list(r.spoiler_spans or []),
                sentiment_label=r.sentiment_label,
                sentiment_score=float(r.sentiment_score) if r.sentiment_score is not None else None,
                news_source_count=r.news_source_count,
                vote_count=int(vc or 0),
            )
            for r, nickname, vc in rows
        ]

    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return None
        if rating is not None:
            row.rating = max(0.5, min(5.0, float(rating)))
        if body is not None:
            row.body = body
            # body가 바뀌면 이전 스포일러 스팬·감정분석은 무효 — 백그라운드 재감지 전까지 초기화.
            row.spoiler_spans = []
            row.sentiment_label = None
            row.sentiment_score = None
        await self._session.commit()
        await self._update_movie_rating(row.movie_id)
        return ReviewDto(
            id=row.id,
            user_id=row.user_id,
            movie_id=row.movie_id,
            rating=float(row.rating or 0),
            body=row.body or "",
            action_at=row.created_at,
            spoiler_spans=list(row.spoiler_spans or []),
        )

    async def update_spoiler_spans(self, review_id: int, spans: list[dict[str, Any]]) -> None:
        """백그라운드 감지 결과 반영 — 실패해도 리뷰 저장 자체는 이미 성공."""
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return
        row.spoiler_spans = spans
        await self._session.commit()

    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        result = (
            await self._session.execute(
                select(
                    func.avg(MovaReview.rating).label("avg"),
                    func.count(MovaReview.id).label("cnt"),
                ).where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.rating.isnot(None),
                )
            )
        ).one()
        return MovieRatingSummaryDto(
            movie_id=movie_id,
            average_rating=round(float(result.avg or 0), 2),
            review_count=int(result.cnt or 0),
        )

    async def delete_review(self, review_id: int) -> bool:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return False
        movie_id = row.movie_id
        await self._session.delete(row)
        await self._session.commit()
        await self._update_movie_rating(movie_id)
        return True

    async def add_comment(self, review_id: int, user_id: int, body: str) -> ReviewCommentDto:
        row = MovaReviewComment(review_id=review_id, user_id=user_id, body=body)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        nickname = (
            await self._session.execute(select(User.nickname).where(User.id == user_id))
        ).scalar_one_or_none()
        return ReviewCommentDto(
            id=row.id,
            review_id=row.review_id,
            user_id=row.user_id,
            nickname=nickname or "",
            body=row.body,
            created_at=row.created_at,
        )

    async def get_comments_by_review(self, review_id: int) -> list[ReviewCommentDto]:
        rows = (
            await self._session.execute(
                select(MovaReviewComment, User.nickname)
                .join(User, MovaReviewComment.user_id == User.id)
                .where(MovaReviewComment.review_id == review_id)
                .order_by(MovaReviewComment.created_at.asc())
            )
        ).all()
        return [
            ReviewCommentDto(
                id=c.id,
                review_id=c.review_id,
                user_id=c.user_id,
                nickname=nickname or "",
                body=c.body,
                created_at=c.created_at,
            )
            for c, nickname in rows
        ]

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        row = (
            await self._session.execute(
                select(MovaReviewComment).where(
                    MovaReviewComment.id == comment_id,
                    MovaReviewComment.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def get_body_for_embedding(self, review_id: int) -> str | None:
        row = (
            await self._session.execute(select(MovaReview.body).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None or not row.strip():
            return None
        return row

    async def list_missing_embedding(self, limit: int | None) -> list[tuple[int, str]]:
        stmt = (
            select(MovaReview.id, MovaReview.body)
            .where(MovaReview.embedding.is_(None), MovaReview.body.is_not(None))
            .order_by(MovaReview.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).all()
        return [(rid, body) for rid, body in rows if body and body.strip()]

    async def update_embedding(self, review_id: int, embedding: list[float]) -> None:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return
        row.embedding = embedding
        await self._session.commit()

    async def list_embedded_reviews_by_user(
        self, user_id: int
    ) -> list[tuple[int, float, list[float], str | None, float | None]]:
        rows = (
            await self._session.execute(
                select(
                    MovaReview.id,
                    MovaReview.rating,
                    MovaReview.embedding,
                    MovaReview.sentiment_label,
                    MovaReview.sentiment_score,
                ).where(
                    MovaReview.user_id == user_id,
                    MovaReview.embedding.is_not(None),
                    MovaReview.rating.is_not(None),
                )
            )
        ).all()
        return [
            (
                rid,
                float(rating),
                list(embedding),
                s_label,
                float(s_score) if s_score is not None else None,
            )
            for rid, rating, embedding, s_label, s_score in rows
        ]

    async def list_missing_sentiment(self, limit: int | None) -> list[tuple[int, str]]:
        stmt = (
            select(MovaReview.id, MovaReview.body)
            .where(MovaReview.sentiment_label.is_(None), MovaReview.body.is_not(None))
            .order_by(MovaReview.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).all()
        return [(rid, body) for rid, body in rows if body and body.strip()]

    async def update_sentiment(self, review_id: int, label: str, score: float) -> None:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None:
            return
        row.sentiment_label = label
        row.sentiment_score = score
        await self._session.commit()

    async def update_rating_if_null(self, review_id: int, rating: float) -> bool:
        row = (
            await self._session.execute(select(MovaReview).where(MovaReview.id == review_id))
        ).scalar_one_or_none()
        if row is None or row.rating is not None:
            return False
        row.rating = max(0.5, min(5.0, float(rating)))
        await self._session.commit()
        await self._update_movie_rating(row.movie_id)
        return True

    async def get_sentiment_summary(self, movie_id: int) -> tuple[int, int, int]:
        rows = (
            await self._session.execute(
                select(MovaReview.sentiment_label, func.count(MovaReview.id))
                .where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.sentiment_label.is_not(None),
                )
                .group_by(MovaReview.sentiment_label)
            )
        ).all()
        positive = 0
        negative = 0
        for label, cnt in rows:
            if label == "긍정":
                positive = int(cnt)
            elif label == "부정":
                negative = int(cnt)
        return positive, negative, positive + negative

    async def toggle_vote(self, review_id: int, user_id: int) -> tuple[bool, int]:
        existing = (
            await self._session.execute(
                select(MovaReviewVote).where(
                    MovaReviewVote.review_id == review_id,
                    MovaReviewVote.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            await self._session.delete(existing)
            await self._session.commit()
            count = await self.get_vote_count(review_id)
            return False, count
        self._session.add(MovaReviewVote(review_id=review_id, user_id=user_id))
        await self._session.commit()
        count = await self.get_vote_count(review_id)
        return True, count

    async def get_vote_count(self, review_id: int) -> int:
        result = (
            await self._session.execute(
                select(func.count(MovaReviewVote.id)).where(MovaReviewVote.review_id == review_id)
            )
        ).scalar_one()
        return int(result or 0)

    async def has_voted(self, review_id: int, user_id: int) -> bool:
        row = (
            await self._session.execute(
                select(MovaReviewVote.id)
                .where(
                    MovaReviewVote.review_id == review_id,
                    MovaReviewVote.user_id == user_id,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return row is not None

    async def _update_movie_rating(self, movie_id: int) -> None:
        """reviews upsert 후 movies.rating 갱신."""
        result = (
            await self._session.execute(
                select(func.avg(MovaReview.rating)).where(
                    MovaReview.movie_id == movie_id,
                    MovaReview.rating.isnot(None),
                )
            )
        ).scalar_one_or_none()
        # 리뷰가 0건이 되면 rating을 건드리지 않는다 — movies.rating은 TMDB
        # 유래 기준 평점인데 0.0으로 덮으면 복원 경로가 없어(다음 재임포트까지)
        # 가중평점 정렬·게임 풀(rating>=3.3)에서 영구 강등된다(2026-09-11 리뷰).
        if result is None:
            return
        movie = (
            await self._session.execute(select(MovaMovie).where(MovaMovie.id == movie_id))
        ).scalar_one_or_none()
        if movie:
            movie.rating = round(float(result), 2)
            await self._session.commit()
