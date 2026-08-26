"""리프레시 토큰 — Redis 저장, 로테이션 방식. 재사용 감지 시 세션 계열(family) 전체 폐기.

viewer의 redis_session_store_adapter.py/redis_pending_identity_repository.py와 같은 redis
서비스(REDIS_URL)를 재사용하되, 키 접두사를 "auth:"로 분리해 viewer의 "viewer:*" 키와
겹치지 않게 한다.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta

import redis

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_REFRESH_TTL = timedelta(days=14)


class ReuseDetected(Exception):
    """이미 사용(rotate)된 리프레시 토큰이 다시 제출됨 — 세션 계열 탈취 의심."""


@dataclass(frozen=True)
class RotatedToken:
    jti: str
    family_id: str
    sub: str
    aud: str
    roles: list[str]


class RefreshTokenStore:
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def issue(
        self, *, sub: str, aud: str, roles: list[str], family_id: str | None = None
    ) -> tuple[str, str]:
        family_id = family_id or secrets.token_urlsafe(16)
        jti = secrets.token_urlsafe(24)
        payload = json.dumps(
            {"sub": sub, "aud": aud, "roles": roles, "family_id": family_id, "used": False}
        )
        self._client.set(f"auth:refresh:{jti}", payload, ex=int(_REFRESH_TTL.total_seconds()))
        return jti, family_id

    def rotate(self, *, jti: str) -> RotatedToken:
        raw = self._client.get(f"auth:refresh:{jti}")
        if raw is None:
            raise ReuseDetected("리프레시 토큰이 존재하지 않거나 만료되었습니다.")

        data = json.loads(raw)
        family_id = data["family_id"]
        if data["used"] or self.is_family_revoked(family_id):
            self.revoke_family(family_id)
            raise ReuseDetected(f"이미 사용된 리프레시 토큰 재사용 감지: family={family_id}")

        data["used"] = True
        self._client.set(
            f"auth:refresh:{jti}", json.dumps(data), ex=int(_REFRESH_TTL.total_seconds())
        )

        new_jti, _ = self.issue(
            sub=data["sub"], aud=data["aud"], roles=data["roles"], family_id=family_id
        )
        return RotatedToken(
            jti=new_jti, family_id=family_id, sub=data["sub"], aud=data["aud"], roles=data["roles"]
        )

    def revoke_family(self, family_id: str) -> None:
        self._client.set(
            f"auth:family:{family_id}:revoked", "1", ex=int(_REFRESH_TTL.total_seconds())
        )

    def is_family_revoked(self, family_id: str) -> bool:
        return self._client.get(f"auth:family:{family_id}:revoked") is not None
