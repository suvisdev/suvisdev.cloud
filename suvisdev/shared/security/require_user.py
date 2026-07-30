"""로그인 가드 — 세션 JWT를 검증하고 role과 무관하게 통과시킨다(본인 확인용).

require_admin.py와 동일하게 서명 검증된 JWT만 신뢰한다. role 체크가 없다는 점만
다르다 — 마이페이지 닉네임 변경처럼 "로그인만 하면 되지만 본인 것만" 건드려야
하는 엔드포인트에서, 요청자 user_id와 리소스 소유자를 대조하는 데 쓴다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException

_JWT_SECRET = os.getenv("JWT_SECRET", "")


@dataclass(frozen=True)
class UserPrincipal:
    user_id: int
    username: str


def require_user(authorization: str | None = Header(default=None)) -> UserPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.") from e

    return UserPrincipal(user_id=int(claims["sub"]), username=claims["username"])
