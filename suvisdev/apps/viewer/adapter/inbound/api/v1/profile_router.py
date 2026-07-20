from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from viewer.app.ports.input.profile_use_case import ProfileUseCase
from viewer.dependencies.profile_provider import get_profile_use_case

profile_router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileResponse(BaseModel):
    id: int
    username: str
    nickname: str
    email: str
    gender: str
    preferred_genres: list[str]
    providers: list[str]


@profile_router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: int,
    profile: ProfileUseCase = Depends(get_profile_use_case),
) -> ProfileResponse:
    result = await profile.get_profile(user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="회원 정보를 찾을 수 없습니다.")
    return ProfileResponse(
        id=result.id,
        username=result.username,
        nickname=result.nickname,
        email=result.email,
        gender=result.gender,
        preferred_genres=result.preferred_genres,
        providers=result.providers,
    )
