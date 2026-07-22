"""GET /mova/whoami — auth 게이트웨이 RS256 토큰 검증 데모 엔드포인트.

기존 mova 라우트는 건드리지 않는다. RoleChecker 패턴을 시연하는 용도의 신규
엔드포인트 1개."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mova.dependencies.require_auth import RoleChecker
from shared.security.token_verifier import TokenPayload

whoami_router = APIRouter()


class WhoamiResponse(BaseModel):
    sub: str
    roles: list[str]
    aud: str


@whoami_router.get("/whoami", response_model=WhoamiResponse)
async def whoami(user: TokenPayload = Depends(RoleChecker("admin", "user"))) -> WhoamiResponse:
    return WhoamiResponse(sub=user.sub, roles=user.roles, aud=user.aud)
