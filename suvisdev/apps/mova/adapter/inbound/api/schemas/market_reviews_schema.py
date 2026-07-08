from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewActivityCreateSchema(BaseModel):
    user_id: int
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
    user_id: int
    movie_id: int
    rating: float
    body: str = ""


class ReviewSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: float
    body: str
    action_at: datetime


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


class MovieRatingSummarySchema(BaseModel):
    movie_id: int
    average_rating: float
    review_count: int


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
