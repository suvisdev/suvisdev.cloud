"""리프레시 토큰 — Redis 저장, 로테이션 방식. 재사용 감지 시 세션 계열(family) 전체 폐기.

viewer의 redis_session_store_adapter.py/redis_pending_identity_repository.py와 같은 redis
서비스(REDIS_URL)를 재사용하되, 키 접두사를 "auth:"로 분리해 viewer의 "viewer:*" 키와
겹치지 않게 한다.
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass
from datetime import timedelta

import redis

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_REFRESH_TTL = timedelta(days=14)
# 세션 저장 형식 표식(2026-10-20). 없는 옛 세션은 admins 로그인 sub가 양수(admins.id)라
# users.id로 잘못 해석될 수 있다 — services가 admin 옛 세션을 걸러낸다.
_SESSION_VERSION = 2
# 같은 refresh가 거의 동시에 두 번 오면(웹 BFF 다중 인스턴스) 두 번째를 재사용 공격으로
# 보지 않고 첫 회전 결과를 그대로 돌려주는 유예 시간.
_GRACE_SECONDS = 10


class ReuseDetected(Exception):
    """이미 사용(rotate)된 리프레시 토큰이 다시 제출됨 — 세션 계열 탈취 의심."""


@dataclass(frozen=True)
class RotatedToken:
    jti: str
    family_id: str
    sub: str
    aud: str
    roles: list[str]
    legacy: bool = False  # _SESSION_VERSION 표식 없이 저장된 옛 세션에서 회전했는가


class RefreshTokenStore:
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def issue(
        self, *, sub: str, aud: str, roles: list[str], family_id: str | None = None
    ) -> tuple[str, str]:
        family_id = family_id or secrets.token_urlsafe(16)
        jti = secrets.token_urlsafe(24)
        payload = json.dumps(
            {
                "sub": sub,
                "aud": aud,
                "roles": roles,
                "family_id": family_id,
                "used": False,
                "sv": _SESSION_VERSION,
            }
        )
        self._client.set(f"auth:refresh:{jti}", payload, ex=int(_REFRESH_TTL.total_seconds()))
        return jti, family_id

    def rotate(self, *, jti: str) -> RotatedToken:
        raw = self._client.get(f"auth:refresh:{jti}")
        if raw is None:
            raise ReuseDetected("리프레시 토큰이 존재하지 않거나 만료되었습니다.")

        data = json.loads(raw)
        family_id = data["family_id"]
        if data["used"] and not self.is_family_revoked(family_id):
            grace = self._client.get(f"auth:refresh:grace:{jti}")
            if grace is not None:  # 유예 안의 동시 요청 — 같은 새 토큰을 돌려준다
                return RotatedToken(**json.loads(grace))
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
        rotated = RotatedToken(
            jti=new_jti,
            family_id=family_id,
            sub=data["sub"],
            aud=data["aud"],
            roles=data["roles"],
            legacy="sv" not in data,
        )
        self._client.set(
            f"auth:refresh:grace:{jti}", json.dumps(asdict(rotated)), ex=_GRACE_SECONDS
        )
        return rotated

    def revoke_family(self, family_id: str) -> None:
        self._client.set(
            f"auth:family:{family_id}:revoked", "1", ex=int(_REFRESH_TTL.total_seconds())
        )

    def is_family_revoked(self, family_id: str) -> bool:
        return self._client.get(f"auth:family:{family_id}:revoked") is not None
