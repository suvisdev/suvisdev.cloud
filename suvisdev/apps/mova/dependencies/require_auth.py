"""auth 게이트웨이 RS256 토큰 검증 데모 — RoleChecker 패턴을 mova에 시연.

shared.security만 import한다(apps.auth는 import하지 않음 — auth-isolation 계약).
RoleChecker 자체는 mova 안에 작게 중복 정의한다(다른 앱들도 각자 자기 파일에 둘 것).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from shared.security.token_verifier import TokenPayload, verify_token

_SERVICE_AUD = "suvis-mova"


async def get_current_user(request: Request) -> TokenPayload:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 없습니다.")
    token = auth_header.removeprefix("Bearer ")
    try:
        return verify_token(token, aud=_SERVICE_AUD)
    except Exception as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.") from e


class RoleChecker:
    def __init__(self, *allowed: str) -> None:
        self._allowed = set(allowed)

    def __call__(self, user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not self._allowed & set(user.roles):
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        return user
