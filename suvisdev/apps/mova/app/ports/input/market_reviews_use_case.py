"""리뷰 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mova.app.dtos.market_reviews_dto import (
    MovieRatingSummaryDto,
    MovieSentimentSummaryDto,
    ReviewActivityDto,
    ReviewCommentDto,
    ReviewDto,
    ReviewVoteResultDto,
    ReviewWithUserDto,
)


class ReviewsUseCase(ABC):
    @abstractmethod
    async def add_activity(
        self, user_id: int, movie_id: int, action_type: str
    ) -> ReviewActivityDto:
        pass

    @abstractmethod
    async def add_review(
        self, user_id: int, movie_id: int, rating: float | None, body: str | None
    ) -> ReviewDto:
        pass

    @abstractmethod
    async def get_by_id(self, review_id: int) -> ReviewDto | None:
        pass

    @abstractmethod
    async def get_by_movie(self, movie_id: int, limit: int, offset: int) -> list[ReviewWithUserDto]:
        pass

    @abstractmethod
    async def update_review(
        self, review_id: int, rating: float | None, body: str | None
    ) -> ReviewDto | None:
        pass

    @abstractmethod
    async def get_rating_summary(self, movie_id: int) -> MovieRatingSummaryDto:
        pass

    @abstractmethod
    async def delete_review(self, review_id: int) -> bool:
        pass

    @abstractmethod
    async def add_comment(self, review_id: int, user_id: int, body: str) -> ReviewCommentDto:
        pass

    @abstractmethod
    async def get_comments(self, review_id: int) -> list[ReviewCommentDto]:
        pass

    @abstractmethod
    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        pass

    @abstractmethod
    async def get_sentiment_summary(self, movie_id: int) -> MovieSentimentSummaryDto:
        pass

    @abstractmethod
    async def toggle_vote(self, review_id: int, user_id: int) -> ReviewVoteResultDto:
        pass
