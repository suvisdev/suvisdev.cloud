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


def verify_token(token: str, aud: str) -> TokenPayload:
    claims = jwt.decode(
        token,
        _load_public_key(),
        algorithms=["RS256"],
        audience=aud,
    )
    return TokenPayload(**claims)
