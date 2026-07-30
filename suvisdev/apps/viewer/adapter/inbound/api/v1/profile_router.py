from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from shared.security.require_user import UserPrincipal, require_user
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


class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)


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


@profile_router.patch("/{user_id}", response_model=ProfileResponse)
async def update_nickname(
    user_id: int,
    payload: UpdateNicknameRequest,
    principal: UserPrincipal = Depends(require_user),
    profile: ProfileUseCase = Depends(get_profile_use_case),
) -> ProfileResponse:
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인 정보만 수정할 수 있습니다.")
    result = await profile.update_nickname(user_id, payload.nickname.strip())
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
