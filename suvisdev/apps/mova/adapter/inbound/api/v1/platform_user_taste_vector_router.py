"""GET /mova/taste/me — 본인 취향 벡터 상태 조회."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.security.require_user import UserPrincipal, require_user

from mova.adapter.inbound.api.schemas.platform_user_taste_vector_schema import (
    UserTasteVectorSchema,
)
from mova.app.use_cases.platform_user_taste_vector_interactor import (
    UserTasteVectorRecomputeInteractor,
)
from mova.dependencies.platform_user_taste_vector_provider import (
    get_user_taste_vector_recompute_use_case,
)

platform_user_taste_vector_router = APIRouter(tags=["mova-taste"])


@platform_user_taste_vector_router.get("/taste/me", response_model=UserTasteVectorSchema)
async def get_my_taste_vector(
    principal: UserPrincipal = Depends(require_user),
    use_case: UserTasteVectorRecomputeInteractor = Depends(
        get_user_taste_vector_recompute_use_case
    ),
) -> UserTasteVectorSchema:
    """리뷰를 한 번도 안 남긴 유저는 행 자체가 없다 — has_vector=False로 응답."""
    dto = await use_case.get_for_user(principal.user_id)
    if dto is None:
        return UserTasteVectorSchema(has_vector=False, review_count=0, updated_at=None)
    return dto.to_schema()
