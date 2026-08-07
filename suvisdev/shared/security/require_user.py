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


def optional_user(authorization: str | None = Header(default=None)) -> UserPrincipal | None:
    """로그인해도 되고 안 해도 되는 엔드포인트용 — 토큰이 있으면 검증해서 신원을
    주고, 없으면 `None`(익명)을 준다.

    `/mova/chat`처럼 **비로그인 사용을 의도적으로 허용**하지만, 로그인한 요청은
    본인으로만 처리해야 하는 곳에 쓴다. 요청 바디의 `user_id`를 그대로 믿으면
    남의 대화·선호로 개인화된 답을 받고 남의 이력에 기록까지 남길 수 있다
    (2026-08-07 수정).

    **토큰이 붙었는데 유효하지 않으면 익명으로 강등하지 않고 401을 낸다** —
    만료된 세션을 조용히 익명 처리하면 사용자는 개인화가 왜 끊겼는지 알 수 없다.
    """
    if authorization is None or not authorization.strip():
        return None
    return require_user(authorization)
