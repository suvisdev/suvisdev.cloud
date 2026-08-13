"""RS256 발급/검증(JwtAdapter) + auth 서비스 자체 라우트 보호용 RBAC dependency."""

from __future__ import annotations

import base64
import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request
from jwt.algorithms import RSAAlgorithm

from auth.schemas import TokenPayload

# viewer HS256 세션 TTL(7일)과 일치. 2026-08-13까지 10분이었는데 프론트가
# refresh_token 흐름을 안 태워서 10분마다 mypage 진입·게임 스코어 저장 등
# 모든 mova 인증 API가 401 → 재로그인 유도되던 이슈의 즉시 fix.
# refresh 흐름 도입 시 다시 짧게 되돌릴 것.
_ACCESS_TTL_DEFAULT_MIN = 60 * 24 * 7


def _load_private_key() -> str:
    """개인키는 호출 시점에만 읽는다 — 모듈 import 시점에 읽으면 개인키 없는
    컨테이너(main/auth_main 소비자 쪽)의 부팅이 깨진다."""
    raw = os.getenv("JWT_PRIVATE_KEY_B64", "")
    if not raw:
        raise RuntimeError("JWT_PRIVATE_KEY_B64가 설정되지 않았습니다.")
    return base64.b64decode(raw).decode("utf-8")


def _load_public_key() -> str:
    raw = os.getenv("JWT_PUBLIC_KEY_B64", "")
    if not raw:
        raise RuntimeError("JWT_PUBLIC_KEY_B64가 설정되지 않았습니다.")
    return base64.b64decode(raw).decode("utf-8")


def _key_id() -> str:
    return os.getenv("JWT_KID", "auth-key-1")


class JwtAdapter:
    """RS256 발급/검증. 개인키 접근은 이 클래스의 issue 계열 메서드 안에서만 일어난다."""

    def issue_access_token(
        self, sub: str, roles: list[str], aud: str, expires_min: int = _ACCESS_TTL_DEFAULT_MIN
    ) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": sub,
            "roles": roles,
            "aud": aud,
            "iat": now,
            "exp": now + timedelta(minutes=expires_min),
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(
            claims,
            _load_private_key(),
            algorithm="RS256",
            headers={"kid": _key_id()},
        )

    def verify(self, token: str, aud: str) -> TokenPayload:
        claims = jwt.decode(
            token,
            _load_public_key(),
            algorithms=["RS256"],
            audience=aud,
        )
        return TokenPayload(**claims)

    def build_jwks(self) -> dict[str, Any]:
        algorithm = RSAAlgorithm(RSAAlgorithm.SHA256)
        public_key = algorithm.prepare_key(_load_public_key())
        jwk = json.loads(algorithm.to_jwk(public_key))
        jwk.update({"kid": _key_id(), "use": "sig", "alg": "RS256"})
        return {"keys": [jwk]}


_issuer = JwtAdapter()


async def get_current_user(request: Request) -> TokenPayload:
    """auth 서비스 자체 라우트 보호용. 현재는 어떤 라우트도 이 dependency를 쓰지 않음
    (patterns 대기) — /login, /logout, /refresh, /callback, /.well-known/jwks.json은
    모두 공개 엔드포인트다."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 없습니다.")
    token = auth_header.removeprefix("Bearer ")
    try:
        return _issuer.verify(token, aud="suvis-auth")
    except Exception as e:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.") from e


class RoleChecker:
    def __init__(self, *allowed: str) -> None:
        self._allowed = set(allowed)

    def __call__(self, user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not self._allowed & set(user.roles):
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        return user
