"""리뷰 라우터 — /mova/reviews"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from shared.security.require_user import UserPrincipal, require_user

from mova.adapter.inbound.api.schemas.market_reviews_schema import (
    MovieRatingSummarySchema,
    MovieSentimentSummarySchema,
    ReviewActivityCreateSchema,
    ReviewActivitySchema,
    ReviewCommentCreateSchema,
    ReviewCommentSchema,
    ReviewCreateSchema,
    ReviewSchema,
    ReviewUpdateSchema,
    ReviewWithUserSchema,
)
from mova.app.ports.input.market_reviews_use_case import ReviewsUseCase
from mova.app.ports.output.market_reviews_errors import ReviewNotWatchedError, ReviewValidationError
from mova.app.use_cases.platform_user_taste_vector_interactor import (
    UserTasteVectorRecomputeInteractor,
)
from mova.app.use_cases.review_embedding_backfill_interactor import (
    ReviewEmbeddingBackfillInteractor,
)
from mova.app.use_cases.review_sentiment_backfill_interactor import (
    ReviewSentimentBackfillInteractor,
)
from mova.app.use_cases.review_spoiler_backfill_interactor import (
    ReviewSpoilerBackfillInteractor,
)
from mova.dependencies.market_reviews_provider import get_reviews_use_case
from mova.dependencies.platform_user_taste_vector_provider import (
    get_user_taste_vector_recompute_use_case,
)
from mova.dependencies.review_embedding_provider import get_review_embedding_backfill_use_case
from mova.dependencies.review_sentiment_provider import get_review_sentiment_backfill_use_case
from mova.dependencies.review_spoiler_provider import get_review_spoiler_backfill_use_case


async def _embed_review_then_recompute_taste(
    embedding_backfill: ReviewEmbeddingBackfillInteractor,
    taste_recompute: UserTasteVectorRecomputeInteractor,
    review_id: int,
    user_id: int,
) -> None:
    """BG task 하나로 두 단계 체이닝 — 리뷰 임베딩 저장 성공 시에만 취향 벡터 재계산.

    임베딩 실패면 취향 벡터는 그대로 두고 다음 크론 안전망이 처리한다.
    두 단계 다 실패해도 리뷰 자체는 이미 저장돼 있으니 요청은 성공 응답.
    """
    outcome = await embedding_backfill.embed_one(review_id)
    if outcome == "succeeded":
        await taste_recompute.recompute_for_user(user_id)


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
    taste_recompute: UserTasteVectorRecomputeInteractor = Depends(
        get_user_taste_vector_recompute_use_case
    ),
    spoiler_backfill: ReviewSpoilerBackfillInteractor = Depends(
        get_review_spoiler_backfill_use_case
    ),
    sentiment_backfill: ReviewSentimentBackfillInteractor = Depends(
        get_review_sentiment_backfill_use_case
    ),
) -> ReviewSchema:
    """별점·감상평 리뷰 저장(재제출 시 기존 리뷰 upsert). 별점만/본문만/둘 다 허용.

    body가 있으면 응답 후 background에서 임베딩 생성 + 성공 시 취향 벡터
    재계산(체이닝). 실패해도 리뷰는 남고 크론이 안전망으로 나중에 잡음.
    body가 없으면 임베딩은 스킵하지만 rating 변경으로도 취향 벡터 후보가 달라질
    수 있으니 recompute만 걸어둔다.
    """
    try:
        dto = await use_case.add_review(principal.user_id, body.movie_id, body.rating, body.body)
    except (ReviewValidationError, ReviewNotWatchedError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    if body.body and body.body.strip():
        background_tasks.add_task(
            _embed_review_then_recompute_taste,
            embedding_backfill,
            taste_recompute,
            dto.id,
            principal.user_id,
        )
        # 스포일러 감지·감정분석도 병렬 백그라운드 — 임베딩/취향 벡터와 서로 독립.
        background_tasks.add_task(spoiler_backfill.detect_one, dto.id)
        background_tasks.add_task(sentiment_backfill.analyze_one, dto.id)
    else:
        background_tasks.add_task(taste_recompute.recompute_for_user, principal.user_id)
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


@market_reviews_router.get(
    "/sentiment/{movie_id}", response_model=MovieSentimentSummarySchema
)
async def get_sentiment_summary(
    movie_id: int,
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> MovieSentimentSummarySchema:
    """영화별 감정분석 요약 — 긍정/부정 비율 + 한 줄 요약."""
    dto = await use_case.get_sentiment_summary(movie_id)
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
    taste_recompute: UserTasteVectorRecomputeInteractor = Depends(
        get_user_taste_vector_recompute_use_case
    ),
    spoiler_backfill: ReviewSpoilerBackfillInteractor = Depends(
        get_review_spoiler_backfill_use_case
    ),
    sentiment_backfill: ReviewSentimentBackfillInteractor = Depends(
        get_review_sentiment_backfill_use_case
    ),
) -> ReviewSchema:
    """리뷰 수정 — 본인 리뷰만 가능(IDOR 방지).

    body/rating이 바뀌었을 가능성이 있으면 background에서 임베딩 재생성 +
    성공 시 취향 벡터 재계산(체이닝). update가 부분 갱신이라 body 유무를
    여기서 못 가려 항상 체인을 건다(embed_one이 body 없으면 자체 스킵).
    """
    existing = await use_case.get_by_id(review_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    if existing.user_id != principal.user_id:
        raise HTTPException(status_code=403, detail="본인 리뷰만 수정할 수 있습니다.")
    dto = await use_case.update_review(review_id, body.rating, body.body)
    if dto is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    background_tasks.add_task(
        _embed_review_then_recompute_taste,
        embedding_backfill,
        taste_recompute,
        review_id,
        existing.user_id,
    )
    # 본문이 바뀌었으면 스포일러 감지·감정분석도 재실행. update_review가 body 변경 시
    # spoiler_spans·sentiment를 초기화하므로 재분석이 필요하다.
    if body.body is not None:
        background_tasks.add_task(spoiler_backfill.detect_one, review_id)
        background_tasks.add_task(sentiment_backfill.analyze_one, review_id)
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


@market_reviews_router.get("/{review_id}/comments", response_model=list[ReviewCommentSchema])
async def get_review_comments(
    review_id: int,
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> list[ReviewCommentSchema]:
    """리뷰 댓글 목록(작성순) — 공개."""
    dtos = await use_case.get_comments(review_id)
    return [d.to_schema() for d in dtos]


@market_reviews_router.post(
    "/{review_id}/comments", response_model=ReviewCommentSchema, status_code=201
)
async def add_review_comment(
    review_id: int,
    body: ReviewCommentCreateSchema,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> ReviewCommentSchema:
    """리뷰 댓글 작성 — 로그인 필수, 신원은 토큰에서만."""
    existing = await use_case.get_by_id(review_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    try:
        dto = await use_case.add_comment(review_id, principal.user_id, body.body)
    except ReviewValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return dto.to_schema()


@market_reviews_router.delete("/comments/{comment_id}", status_code=200)
async def delete_review_comment(
    comment_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: ReviewsUseCase = Depends(get_reviews_use_case),
) -> dict[str, str]:
    """본인 댓글 삭제 — 소유권을 쿼리에 함께 걸어 없는 것/남의 것을 구분하지 않는다."""
    ok = await use_case.delete_comment(comment_id, principal.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    return {"status": "deleted"}
