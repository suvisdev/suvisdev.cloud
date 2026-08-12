"""RBAC 가드 — auth 게이트웨이가 발급한 RS256 JWT를 검증하고 role=admin만 통과시킨다.

roles 배열은 로그인 시 auth 게이트웨이가 ADMIN_EMAILS 기준으로 산출해 토큰
claim에 넣은 값이다. 클라이언트가 보내는 어떤 값도 신뢰하지 않고, 오직 서명
검증된 JWT의 roles만 본다.

require_user.py와 마찬가지로 2026-08-12에 HS256 → RS256으로 통일했다.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from shared.security.token_verifier import verify_token

_MOVA_AUD = "suvis-mova"


@dataclass(frozen=True)
class AdminPrincipal:
    user_id: int
    username: str


def require_admin(authorization: str | None = Header(default=None)) -> AdminPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = verify_token(token, aud=_MOVA_AUD)
    except Exception as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.") from e

    if "admin" not in payload.roles:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    return AdminPrincipal(user_id=int(payload.sub), username="")
