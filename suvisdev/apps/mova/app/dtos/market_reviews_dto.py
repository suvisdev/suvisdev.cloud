"""리뷰 DTO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mova.adapter.inbound.api.schemas.market_reviews_schema import (
        MovieRatingSummarySchema,
        MovieSentimentSummarySchema,
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
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    news_source_count: int | None = None

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
            sentiment_label=self.sentiment_label,
            sentiment_score=self.sentiment_score,
            news_source_count=self.news_source_count,
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


@dataclass(frozen=True)
class MovieSentimentSummaryDto:
    movie_id: int
    positive_count: int
    negative_count: int
    total_count: int

    @property
    def positive_ratio(self) -> float:
        return self.positive_count / self.total_count if self.total_count else 0.0

    @property
    def summary(self) -> str:
        if self.total_count == 0:
            return "감정분석 데이터가 아직 없습니다."
        ratio = self.positive_ratio
        if ratio >= 0.8:
            return "관객 반응이 매우 좋습니다."
        if ratio >= 0.6:
            return "대체로 긍정적인 반응입니다."
        if ratio >= 0.4:
            return "호불호가 갈리는 작품입니다."
        if ratio >= 0.2:
            return "부정적인 반응이 다소 많습니다."
        return "관객 반응이 좋지 않습니다."

    def to_schema(self) -> MovieSentimentSummarySchema:
        from mova.adapter.inbound.api.schemas.market_reviews_schema import (
            MovieSentimentSummarySchema,
        )

        return MovieSentimentSummarySchema(
            movie_id=self.movie_id,
            positive_count=self.positive_count,
            negative_count=self.negative_count,
            total_count=self.total_count,
            positive_ratio=round(self.positive_ratio, 2),
            summary=self.summary,
        )
