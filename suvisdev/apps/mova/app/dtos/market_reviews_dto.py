"""리뷰 DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReviewActivityDto:
    id: int
    user_id: int
    movie_id: int
    action_type: str
    action_at: datetime

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewActivitySchema

        return ReviewActivitySchema(
            id=self.id,
            user_id=self.user_id,
            movie_id=self.movie_id,
            action_type=self.action_type,
            action_at=self.action_at,
        )


@dataclass(frozen=True)
class ReviewDto:
    id: int
    user_id: int
    movie_id: int
    rating: float
    body: str
    action_at: datetime

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewSchema

        return ReviewSchema(
            id=self.id,
            user_id=self.user_id,
            movie_id=self.movie_id,
            rating=self.rating,
            body=self.body,
            action_at=self.action_at,
        )


@dataclass(frozen=True)
class ReviewWithUserDto:
    id: int
    user_id: int
    nickname: str
    movie_id: int
    rating: float
    body: str
    created_at: datetime

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewWithUserSchema

        return ReviewWithUserSchema(
            id=self.id,
            user_id=self.user_id,
            nickname=self.nickname,
            movie_id=self.movie_id,
            rating=self.rating,
            body=self.body,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class MovieRatingSummaryDto:
    movie_id: int
    average_rating: float
    review_count: int

    def to_schema(self) -> object:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import MovieRatingSummarySchema

        return MovieRatingSummarySchema(
            movie_id=self.movie_id,
            average_rating=self.average_rating,
            review_count=self.review_count,
        )
