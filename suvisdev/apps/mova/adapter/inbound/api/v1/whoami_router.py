"""GET /mova/whoami — auth 게이트웨이 RS256 토큰 검증 데모 엔드포인트.

기존 mova 라우트는 건드리지 않는다. RoleChecker 패턴을 시연하는 용도의 신규
엔드포인트 1개."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mova.dependencies.require_auth import RoleChecker
from shared.security.token_verifier import TokenPayload
from viewer.adapter.outbound.orm.user_orm import get_viewer_user_nicknames

whoami_router = APIRouter()


class WhoamiResponse(BaseModel):
    sub: str
    roles: list[str]
    aud: str
    username: str  # 표시용 이름(닉네임) — viewer users 테이블에 없으면 빈 문자열


@whoami_router.get("/whoami", response_model=WhoamiResponse)
async def whoami(user: TokenPayload = Depends(RoleChecker("admin", "user"))) -> WhoamiResponse:
    nicknames = await get_viewer_user_nicknames({int(user.sub)})
    return WhoamiResponse(
        sub=user.sub,
        roles=user.roles,
        aud=user.aud,
        username=nicknames.get(int(user.sub), ""),
    )
