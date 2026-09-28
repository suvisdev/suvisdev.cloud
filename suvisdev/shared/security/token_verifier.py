"""auth 게이트웨이가 발급한 RS256 토큰을 검증하는 공용 모듈.

apps.auth를 import하지 않는다(격리 유지, auth-isolation import-linter 계약) — 공개키
로드와 jwt.decode 로직을 이 파일 안에서 독립적으로 다시 구현한다. 검증 로직은
apps/auth/adapter/outbound/jwt_adapter.py의 verify()와 의도적으로 동일하다.
"""

from __future__ import annotations

import base64
import os

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    roles: list[str]
    aud: str
    exp: int
    iat: int
    jti: str


def _load_public_key() -> str:
    raw = os.getenv("JWT_PUBLIC_KEY_B64", "")
    if not raw:
        raise RuntimeError("JWT_PUBLIC_KEY_B64가 설정되지 않았습니다.")
    return base64.b64decode(raw).decode("utf-8")


def verify_token(token: str, aud: str | list[str]) -> TokenPayload:
    claims = jwt.decode(
        token,
        _load_public_key(),
        algorithms=["RS256"],
        audience=aud,
    )
    return TokenPayload(**claims)


def verify_viewer_session_token(token: str) -> TokenPayload:
    """viewer OAuth·이메일 로그인 세션 JWT(HS256, aud 없음) 검증.

    `viewer.adapter.outbound.cache.redis_session_store_adapter`가 발급하는 형식:
    ``{sub, username, role: str, jti, iat, exp}``. 2026-08-11 정정 이후 mova
    사용자 세션은 이 경로가 실제 발급자이므로, auth 게이트웨이 RS256 토큰과
    나란히 mova 인증에서 수용해야 한다 — 그러지 않으면 OAuth 로그인 사용자가
    mova 인증 API(마이페이지·리뷰·watchlist 등)에서 전부 401을 받는다.

    role(str)을 auth 게이트웨이 계약과 맞추기 위해 ``roles=[role]``로 감싸고,
    페이로드에 없는 aud는 표시용 문자열("viewer-session")로 채운다 —
    RoleChecker는 ``roles``만 검사한다.
    """
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET이 설정되지 않았습니다.")
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    role = claims.get("role", "user")
    return TokenPayload(
        sub=str(claims["sub"]),
        roles=[role],
        aud="viewer-session",
        exp=int(claims["exp"]),
        iat=int(claims.get("iat", 0)),
        jti=str(claims.get("jti", "")),
    )
