"""OAuth 로그인 시작 시 발급하는 CSRF state — Redis 저장, 1회 소비, 짧은 TTL.

로그인을 시작한 시점의 aud(토큰 대상 서비스, 예: suvis-mova)와 return_to(로그인
완료 후 프론트에서 돌아갈 경로)를 state에 같이 묶어 저장한다 — OAuth
프로바이더(Google 등)는 콜백에 state/code/iss만 돌려주고 이 둘을 알지도 못하므로,
콜백에서 다시 요구하면 안 되고 로그인 시작 시점에 저장해둔 값을 state로 조회해
써야 한다.

viewer의 redis_pending_identity_repository.py와 같은 redis 서비스(REDIS_URL)를
재사용하되, 키 접두사를 "auth:"로 분리한다(refresh_store.py와 동일한 관례).
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta

import redis

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class OAuthStateData:
    aud: str
    return_to: str | None


class OAuthStateStore:
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def issue(self, *, aud: str, return_to: str | None = None) -> str:
        state = secrets.token_urlsafe(24)
        payload = json.dumps({"aud": aud, "return_to": return_to})
        self._client.set(f"auth:oauth_state:{state}", payload, ex=int(_STATE_TTL.total_seconds()))
        return state

    def consume(self, state: str) -> OAuthStateData | None:
        """state가 유효하면 1회 소비(삭제)하고 저장돼 있던 aud/return_to를 반환,
        없거나 만료됐으면 None."""
        key = f"auth:oauth_state:{state}"
        raw = self._client.get(key)
        if raw is None:
            return None
        self._client.delete(key)
        data = json.loads(raw)
        return OAuthStateData(aud=data["aud"], return_to=data.get("return_to"))
