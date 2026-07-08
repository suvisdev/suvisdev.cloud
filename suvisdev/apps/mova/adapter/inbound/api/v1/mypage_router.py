from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mova.adapter.inbound.api.schemas.mypage_schema import MypageSchema
from mova.app.ports.input.mypage_use_case import MypageUseCase
from mova.dependencies.mypage_provider import get_mypage_use_case

mypage_router = APIRouter(prefix="/mypage", tags=["mova-mypage"])


@mypage_router.get("/{user_id}", response_model=MypageSchema)
async def get_mypage(
    user_id: int,
    use_case: MypageUseCase = Depends(get_mypage_use_case),
) -> MypageSchema:
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="user_id must be positive")
    dto = await use_case.get_mypage(user_id)
    return dto.to_schema()
