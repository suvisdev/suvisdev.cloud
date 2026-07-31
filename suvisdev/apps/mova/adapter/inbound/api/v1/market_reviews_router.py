"""리뷰 라우터 — /mova/reviews"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mova.adapter.inbound.api.schemas.market_reviews_schema import (
    MovieRatingSummarySchema,
    ReviewActivityCreateSchema,
    ReviewActivitySchema,
    ReviewCreateSchema,
    ReviewSchema,
    ReviewUpdateSchema,
    ReviewWithUserSchema,
)
from mova.app.ports.input.market_reviews_use_case import ReviewsUseCase
from mova.dependencies.market_reviews_provider import get_reviews_use_case
from shared.security.require_user import UserPrincipal, require_user

market_reviews_router = APIRouter(prefix="/reviews", tags=["mova-reviews"])


class _MyselfResponse(BaseModel):
    id: int
    name: str


@market_reviews_router.get("/myself", response_model=_MyselfResponse)
async def introduce_myself() -> _MyselfResponse:
    return _MyselfResponse(id=1, name="평론가 (Critic)")


@market_reviews_router.post("/activity", response_model=ReviewActivitySchema, status_code=201)
async def add_activity(
    body: ReviewActivityCreateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> ReviewActivitySchema:
    """이벤트(favorite/watched/click/not_interested) 기록."""
    dto = await use_case.add_activity(principal.user_id, body.movie_id, body.action_type)
    return dto.to_schema()


@market_reviews_router.post("", response_model=ReviewSchema, status_code=201)
async def add_review(
    body: ReviewCreateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> ReviewSchema:
    """별점·감상평 리뷰 저장(재제출 시 기존 리뷰 upsert)."""
    dto = await use_case.add_review(principal.user_id, body.movie_id, body.rating, body.body)
    return dto.to_schema()


@market_reviews_router.get("/by-movie/{movie_id}", response_model=list[ReviewWithUserSchema])
async def get_reviews_by_movie(
    movie_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> list[ReviewWithUserSchema]:
    """영화별 리뷰 목록."""
    dtos = await use_case.get_by_movie(movie_id, limit, offset)
    return [d.to_schema() for d in dtos]


@market_reviews_router.get("/rating/{movie_id}", response_model=MovieRatingSummarySchema)
async def get_rating_summary(
    movie_id: int,
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> MovieRatingSummarySchema:
    """영화 평균 별점·리뷰 수."""
    dto = await use_case.get_rating_summary(movie_id)
    return dto.to_schema()


@market_reviews_router.patch("/{review_id}", response_model=ReviewSchema)
async def update_review(
    review_id: int,
    body: ReviewUpdateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> ReviewSchema:
    """리뷰 수정 — 본인 리뷰만 가능(IDOR 방지)."""
    existing = await use_case.get_by_id(review_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    if existing.user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="본인 리뷰만 수정할 수 있습니다.")
    dto = await use_case.update_review(review_id, body.rating, body.body)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    return dto.to_schema()
