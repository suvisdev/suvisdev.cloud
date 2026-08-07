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


class UpdateProfileRequest(BaseModel):
    """부분 수정 — 보낸 필드만 바뀐다(둘 다 생략하면 400).

    `preferred_genres`는 교체 저장이다(보낸 목록이 그대로 들어간다). 장르 라벨은
    카탈로그(`tags`)와 함께 늘어나므로 화이트리스트로 막지 않고 개수만 제한한다.
    """

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    preferred_genres: list[str] | None = Field(default=None, max_length=20)


@profile_router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: int,
    principal: UserPrincipal = Depends(require_user),
    profile: ProfileUseCase = Depends(get_profile_use_case),
) -> ProfileResponse:
    # 응답에 email·nickname·gender가 들어간다 — 예전엔 가드가 없어 user_id만 알면
    # 남의 이메일을 그대로 읽을 수 있었다(2026-08-07 수정, mypage와 같은 유형).
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인 정보만 조회할 수 있습니다.")
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
async def update_profile(
    user_id: int,
    payload: UpdateProfileRequest,
    principal: UserPrincipal = Depends(require_user),
    profile: ProfileUseCase = Depends(get_profile_use_case),
) -> ProfileResponse:
    if principal.user_id != user_id:
        raise HTTPException(status_code=403, detail="본인 정보만 수정할 수 있습니다.")
    if payload.nickname is None and payload.preferred_genres is None:
        raise HTTPException(status_code=400, detail="수정할 항목이 없습니다.")

    result = None
    if payload.nickname is not None:
        result = await profile.update_nickname(user_id, payload.nickname.strip())
    if payload.preferred_genres is not None:
        genres = [g.strip() for g in payload.preferred_genres if g.strip()]
        result = await profile.update_preferred_genres(user_id, genres)

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
