"""리뷰 라우터 — /mova/reviews"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
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
from mova.app.ports.output.market_reviews_errors import ReviewNotWatchedError, ReviewValidationError
from mova.app.use_cases.review_embedding_backfill_interactor import (
    ReviewEmbeddingBackfillInteractor,
)
from mova.dependencies.market_reviews_provider import get_reviews_use_case
from mova.dependencies.review_embedding_provider import get_review_embedding_backfill_use_case
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
    background_tasks: BackgroundTasks,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
    embedding_backfill: ReviewEmbeddingBackfillInteractor = Depends(
        get_review_embedding_backfill_use_case
    ),
) -> ReviewSchema:
    """별점·감상평 리뷰 저장(재제출 시 기존 리뷰 upsert). 별점만/본문만/둘 다 허용.

    body가 있으면 응답 후 background에서 임베딩 생성(실패해도 리뷰는 남고
    크론이 안전망으로 나중에 잡음).
    """
    try:
        dto = await use_case.add_review(principal.user_id, body.movie_id, body.rating, body.body)
    except (ReviewValidationError, ReviewNotWatchedError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    if body.body and body.body.strip():
        background_tasks.add_task(embedding_backfill.embed_one, dto.id)
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
    background_tasks: BackgroundTasks,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
    embedding_backfill: ReviewEmbeddingBackfillInteractor = Depends(
        get_review_embedding_backfill_use_case
    ),
) -> ReviewSchema:
    """리뷰 수정 — 본인 리뷰만 가능(IDOR 방지).

    body가 바뀌었을 가능성이 있으면 background에서 임베딩 재생성. add_review와
    달리 body 유무 판정을 여기서 정확히 못 하니(update가 부분 갱신) 항상
    background 잡을 걸어두고, embed_one이 body 없으면 스킵 처리한다.
    """
    existing = await use_case.get_by_id(review_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    if existing.user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="본인 리뷰만 수정할 수 있습니다.")
    dto = await use_case.update_review(review_id, body.rating, body.body)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    background_tasks.add_task(embedding_backfill.embed_one, review_id)
    return dto.to_schema()


@market_reviews_router.delete("/{review_id}", status_code=200)
async def delete_review(
    review_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> dict[str, str]:
    """리뷰 삭제 — 작성자 본인 또는 관리자만 가능(IDOR 방지)."""
    existing = await use_case.get_by_id(review_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    if existing.user_id != principal.user_id and principal.role != "admin":
        raise HTTPException(status_code=403, detail="본인 리뷰만 삭제할 수 있습니다.")
    await use_case.delete_review(review_id)
    return {"status": "deleted"}
