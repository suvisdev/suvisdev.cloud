from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SpoilerSpanSchema(BaseModel):
    """리뷰 본문 안 스포일러 스팬(파이썬 슬라이스 인덱스 규칙)."""

    start: int
    end: int
    text: str


class ReviewActivityCreateSchema(BaseModel):
    """user_id는 요청 바디로 받지 않는다 — require_user principal에서 파생."""

    movie_id: int
    action_type: str


class ReviewActivitySchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    action_type: str
    action_at: datetime


class ReviewActivityWithMovieSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    action_type: str
    action_at: datetime
    movie_title: str
    movie_slug: str
    rating: float | None = None
    body: str | None = None


class ReviewCreateSchema(BaseModel):
    """user_id는 요청 바디로 받지 않는다 — require_user principal에서 파생.

    별점만 / 본문만 / 둘 다 제출을 허용한다 — 둘 다 비어 있으면 인터랙터가
    거부한다(ReviewValidationError, 422).
    """

    movie_id: int
    rating: float | None = Field(default=None, ge=0.5, le=5.0, multiple_of=0.5)
    body: str | None = Field(default=None, max_length=500)


class ReviewSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: float
    body: str
    action_at: datetime
    spoiler_spans: list[SpoilerSpanSchema] = Field(default_factory=list)


class ReviewUpdateSchema(BaseModel):
    rating: float | None = None
    body: str | None = None


class ReviewWithUserSchema(BaseModel):
    id: int
    user_id: int
    nickname: str
    movie_id: int
    rating: float
    body: str
    created_at: datetime
    spoiler_spans: list[SpoilerSpanSchema] = Field(default_factory=list)
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    news_source_count: int | None = None


class ReviewCommentCreateSchema(BaseModel):
    body: str


class ReviewCommentSchema(BaseModel):
    id: int
    review_id: int
    user_id: int
    nickname: str
    body: str
    created_at: datetime


class MovieRatingSummarySchema(BaseModel):
    movie_id: int
    average_rating: float
    review_count: int


class MovieSentimentSummarySchema(BaseModel):
    movie_id: int
    positive_count: int
    negative_count: int
    total_count: int
    positive_ratio: float
    summary: str


class MarketReviewsSchema(BaseModel):
    id: int = Field(0, description="Reviews ID")
    name: str = Field("평론가 (Critic)", description="Critic's name")
    # 작품에 대한 반응을 언어와 별점으로 기록하는 비평가. reviews 테이블 관리

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "평론가 (Critic)",
            }
        }
    }
