"""리뷰 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.market_reviews_schema import (
        MovieRatingSummarySchema,
        ReviewActivitySchema,
        ReviewCommentSchema,
        ReviewSchema,
        ReviewWithUserSchema,
    )
from datetime import datetime


@dataclass(frozen=True)
class ReviewActivityDto:
    id: int
    user_id: int
    movie_id: int
    action_type: str
    action_at: datetime

    def to_schema(self) -> ReviewActivitySchema:
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
    spoiler_spans: list[dict[str, Any]] = field(default_factory=list)

    def to_schema(self) -> ReviewSchema:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewSchema

        return ReviewSchema(
            id=self.id,
            user_id=self.user_id,
            movie_id=self.movie_id,
            rating=self.rating,
            body=self.body,
            action_at=self.action_at,
            spoiler_spans=self.spoiler_spans,  # type: ignore[arg-type]
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
    spoiler_spans: list[dict[str, Any]] = field(default_factory=list)

    def to_schema(self) -> ReviewWithUserSchema:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewWithUserSchema

        return ReviewWithUserSchema(
            id=self.id,
            user_id=self.user_id,
            nickname=self.nickname,
            movie_id=self.movie_id,
            rating=self.rating,
            body=self.body,
            created_at=self.created_at,
            spoiler_spans=self.spoiler_spans,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ReviewCommentDto:
    id: int
    review_id: int
    user_id: int
    nickname: str
    body: str
    created_at: datetime

    def to_schema(self) -> ReviewCommentSchema:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import ReviewCommentSchema

        return ReviewCommentSchema(
            id=self.id,
            review_id=self.review_id,
            user_id=self.user_id,
            nickname=self.nickname,
            body=self.body,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class MovieRatingSummaryDto:
    movie_id: int
    average_rating: float
    review_count: int

    def to_schema(self) -> MovieRatingSummarySchema:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import MovieRatingSummarySchema

        return MovieRatingSummarySchema(
            movie_id=self.movie_id,
            average_rating=self.average_rating,
            review_count=self.review_count,
        )
