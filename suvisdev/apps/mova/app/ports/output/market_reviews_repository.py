"""리뷰 출력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    ReviewActivityDto,
    ReviewDto,
    ReviewWithUserDto,
)


class ReviewsRepositoryPort(ABC):
    @abstractmethod
    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        """이벤트(favorite/watched/click/not_interested) 기록."""

    @abstractmethod
    async def add_review(self, user_id: int, movie_id: int, rating: float, body: str) -> ReviewDto:
        """별점·감상평 리뷰 저장 (action_type=review)."""

    @abstractmethod
    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        """영화별 리뷰 목록 (user join)."""

    @abstractmethod
    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        """리뷰 수정."""

    @abstractmethod
    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        """영화 평균 별점·리뷰 수."""
