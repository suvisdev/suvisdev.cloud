"""RBAC 가드 — 세션 JWT를 검증하고 role=admin만 통과시킨다.

role은 로그인 시 서버(RedisSessionStoreAdapter._resolve_role)가 ADMIN_EMAILS
기준으로 산출해 JWT claim에 넣은 값이다. 클라이언트가 보내는 어떤 값도
신뢰하지 않고, 오직 서명 검증된 JWT의 role claim만 본다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException

_JWT_SECRET = os.getenv("JWT_SECRET", "")


@dataclass(frozen=True)
class AdminPrincipal:
    user_id: int
    username: str


def require_admin(authorization: str | None = Header(default=None)) -> AdminPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.") from e

    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    return AdminPrincipal(user_id=int(claims["sub"]), username=claims["username"])
