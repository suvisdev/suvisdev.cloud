"""리프레시 토큰 — Redis 저장, 로테이션 방식. 재사용 감지 시 세션 계열(family) 전체 폐기.

viewer의 redis_session_store_adapter.py/redis_pending_identity_repository.py와 같은 redis
서비스(REDIS_URL)를 재사용하되, 키 접두사를 "auth:"로 분리해 viewer의 "viewer:*" 키와
겹치지 않게 한다.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import redis

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_REFRESH_TTL = timedelta(days=14)
# 세션 저장 형식 표식(2026-10-20). 없는 옛 세션은 admins 로그인 sub가 양수(admins.id)라
# users.id로 잘못 해석될 수 있다 — services가 admin 옛 세션을 걸러낸다.
_SESSION_VERSION = 2
# 같은 refresh가 거의 동시에 두 번 오면(웹 BFF 다중 인스턴스) 두 번째를 재사용 공격으로
# 보지 않고 첫 회전 결과를 그대로 돌려주는 유예 시간(초).
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


def _now() -> float:
    return time.time()


def _claim_key(jti: str) -> str:
    return f"auth:refresh:claim:{jti}"


def _rotated(data: dict[str, Any], new_jti: str) -> RotatedToken:
    return RotatedToken(
        jti=new_jti,
        family_id=data["family_id"],
        sub=data["sub"],
        aud=data["aud"],
        roles=data["roles"],
        legacy="sv" not in data,
    )


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
        """회전 — 옛 jti마다 `auth:refresh:claim:{jti}` 하나를 **SET NX**로 선점한다(2026-10-20).

        구 버전은 used=True 저장·후속 토큰 저장·유예 결과 저장이 따로 놀아, 그 사이에 같은
        jti가 또 오면 계열 전체를 폐기하거나 서로 다른 후속 토큰을 두 개 발급했다. 지금은
        후속 토큰을 먼저 저장한 뒤 claim(값=후속 jti·시각)을 NX로 건다 — NX가 원자적이라
        이긴 요청 하나만 회전하고, 진 요청은 자기 후속 토큰을 지우고 이긴 쪽 결과를 따른다.
        claim이 곧 사용됨 표시이자 유예 결과라 둘 사이에 틈이 없다.

        이미 claim된 jti가 다시 오면:
        - 유예(_GRACE_SECONDS) 안 + 후속 토큰이 아직 미사용 → 같은 후속 토큰(동시 요청)
        - 유예 안 + 후속도 이미 회전됨(A→B→C 뒤 늦은 A) → 계열은 두고 401만. B를 돌려주면
          클라이언트 쿠키가 이미 쓴 B로 덮여 다음 정상 refresh가 재사용으로 몰린다.
        - 유예 밖 → 재사용 공격으로 보고 계열 폐기
        """
        raw = self._client.get(f"auth:refresh:{jti}")
        if raw is None:
            raise ReuseDetected("리프레시 토큰이 존재하지 않거나 만료되었습니다.")

        data = json.loads(raw)
        family_id = data["family_id"]
        # used=True는 claim 도입 전에 회전된 토큰 — 기존대로 재사용 처리
        if data.get("used") or self.is_family_revoked(family_id):
            self.revoke_family(family_id)
            raise ReuseDetected(f"이미 사용된 리프레시 토큰 재사용 감지: family={family_id}")

        claim = self._client.get(_claim_key(jti))
        if claim is None:
            new_jti, _ = self.issue(
                sub=data["sub"], aud=data["aud"], roles=data["roles"], family_id=family_id
            )
            won = self._client.set(
                _claim_key(jti),
                json.dumps({"next": new_jti, "at": _now()}),
                nx=True,
                ex=int(_REFRESH_TTL.total_seconds()),
            )
            if won:
                return _rotated(data, new_jti)
            self._client.delete(f"auth:refresh:{new_jti}")  # 다른 요청이 먼저 회전했다
            claim = self._client.get(_claim_key(jti))
            if claim is None:  # 이긴 쪽 claim이 그새 사라질 수는 없다(TTL 14일) — 방어적 거부
                raise ReuseDetected("리프레시 토큰 회전 상태를 확인할 수 없습니다.")

        claimed = json.loads(claim)
        if _now() - claimed["at"] <= _GRACE_SECONDS:
            if self._client.get(_claim_key(claimed["next"])) is None:
                return _rotated(data, claimed["next"])
            raise ReuseDetected("이미 다음 토큰으로 넘어간 늦은 중복 요청입니다.")
        self.revoke_family(family_id)
        raise ReuseDetected(f"이미 사용된 리프레시 토큰 재사용 감지: family={family_id}")

    def revoke_family(self, family_id: str) -> None:
        self._client.set(
            f"auth:family:{family_id}:revoked", "1", ex=int(_REFRESH_TTL.total_seconds())
        )

    def is_family_revoked(self, family_id: str) -> bool:
        return self._client.get(f"auth:family:{family_id}:revoked") is not None
