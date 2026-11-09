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


class RefreshSuperseded(ReuseDetected):
    """유예 안의 늦은 중복 요청 — 후속 토큰이 이미 회전돼 있다. 계열은 살아 있으므로
    라우터가 일반 무효(401)와 구분해 409 `refresh_superseded`로 답한다(클라이언트는
    현재 쿠키를 지우지 말고 재시도)."""


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
        - 유예 안 + 후속도 이미 회전됨(A→B→C 뒤 늦은 A) → 계열은 두고 RefreshSuperseded(409). B를 돌려주면
          클라이언트 쿠키가 이미 쓴 B로 덮여 다음 정상 refresh가 재사용으로 몰린다.
        - 유예 밖 → 재사용 공격으로 보고 계열 폐기

        claim 키는 TTL(14일)로만 사라진다는 전제다 — 운영 Redis는 maxmemory 0·noeviction이라 축출이
        없다(2026-10-20 확인). 축출 정책을 켜면 claim만 사라져 옛 토큰이 다시 회전될 수 있으니 이
        전제부터 다시 볼 것.

        남는 한계: 늦은 중복에 B를 돌려준 직후 B가 C로 회전되면, 그 응답이 브라우저에 늦게
        닿아 쿠키가 B로 돌아갈 수 있다. B도 유예 10초 안이면 C를 다시 받아 복구되지만, 10초
        뒤에 B로 갱신하면 재사용으로 폐기된다. 응답 도착 순서는 서버가 알 수 없어 여기서는 막지
        못한다(이 순서가 되려면 10초 안에 회전이 두 번 일어나야 해 드물다).
        """
        raw = self._client.get(f"auth:refresh:{jti}")
        if raw is None:
            raise ReuseDetected("리프레시 토큰이 존재하지 않거나 만료되었습니다.")

        data = json.loads(raw)
        family_id = data["family_id"]
        # used=True는 claim 도입 전에 회전된 토큰 — 기존대로 재사용 처리. 그 전에 배포된 버전엔
        # 유예가 없어 used=True가 곧 재사용이었다(유예 키를 쓴 중간 버전은 운영에 나간 적 없음).
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
                # 폐기 확인과 claim 사이에 로그아웃(계열 폐기)이 끼었으면 회전을 무효로 한다.
                if self.is_family_revoked(family_id):
                    self._client.delete(f"auth:refresh:{new_jti}")
                    raise ReuseDetected("이미 로그아웃된 세션입니다.")
                return _rotated(data, new_jti)
            self._client.delete(f"auth:refresh:{new_jti}")  # 다른 요청이 먼저 회전했다
            claim = self._client.get(_claim_key(jti))
            if claim is None:  # 이긴 쪽 claim이 그새 사라질 수는 없다(TTL 14일) — 방어적 거부
                raise ReuseDetected("리프레시 토큰 회전 상태를 확인할 수 없습니다.")

        claimed = json.loads(claim)
        if _now() - claimed["at"] <= _GRACE_SECONDS:
            if self.is_family_revoked(family_id):
                raise ReuseDetected("이미 로그아웃된 세션입니다.")
            if self._client.get(_claim_key(claimed["next"])) is None:
                return _rotated(data, claimed["next"])
            raise RefreshSuperseded("refresh_superseded")
        self.revoke_family(family_id)
        raise ReuseDetected(f"이미 사용된 리프레시 토큰 재사용 감지: family={family_id}")

    def revoke_by_jti(self, jti: str) -> None:
        """로그아웃 — 회전 여부와 무관하게 토큰 레코드로 계열을 찾아 폐기한다. 회전된 옛
        토큰(A→B→C 뒤 A)으로 로그아웃해도 C까지 끊긴다. 레코드가 없으면(만료) 할 일 없음."""
        raw = self._client.get(f"auth:refresh:{jti}")
        if raw is not None:
            self.revoke_family(json.loads(raw)["family_id"])

    def revoke_family(self, family_id: str) -> None:
        self._client.set(
            f"auth:family:{family_id}:revoked", "1", ex=int(_REFRESH_TTL.total_seconds())
        )

    def is_family_revoked(self, family_id: str) -> bool:
        return self._client.get(f"auth:family:{family_id}:revoked") is not None
