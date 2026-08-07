from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mova.adapter.inbound.api.schemas.mypage_schema import MypageSchema
from mova.app.ports.input.mypage_use_case import MypageUseCase
from mova.dependencies.mypage_provider import get_mypage_use_case
from shared.security.require_user import UserPrincipal, require_user

mypage_router = APIRouter(prefix="/mypage", tags=["mova-mypage"])


@mypage_router.get("/{user_id}", response_model=MypageSchema)
async def get_mypage(
    user_id: int,
    principal: UserPrincipal = Depends(require_user),
    use_case: MypageUseCase = Depends(get_mypage_use_case),
) -> MypageSchema:
    # 닉네임·AI 추천 기록·검색 기록·리뷰·시청 통계가 전부 개인정보다 —
    # 예전엔 가드가 없어 user_id만 알면 남의 마이페이지를 볼 수 있었다(2026-08-07 수정).
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id must be positive")
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인 정보만 조회할 수 있습니다.")
    dto = await use_case.get_mypage(user_id)
    return dto.to_schema()
