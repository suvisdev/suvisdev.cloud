"""약관 동의 대기 중인 신규 OAuth 신원 — Redis에 임시 저장(10분 TTL, 1회 소비)."""

from __future__ import annotations

import json
import os
import secrets
from datetime import timedelta

import redis

from viewer.app.dtos.oauth_dto import OAuthIdentity
from viewer.app.ports.output.pending_identity_repository import PendingIdentityRepository

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_PENDING_TTL = timedelta(minutes=10)


class RedisPendingIdentityRepository(PendingIdentityRepository):
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def save_pending(self, identity: OAuthIdentity) -> str:
        code = secrets.token_urlsafe(24)
        payload = json.dumps(
            {
                "provider": identity.provider,
                "provider_user_id": identity.provider_user_id,
                "email": identity.email,
                "name": identity.name,
            }
        )
        self._client.set(
            f"viewer:oauth_pending:{code}", payload, ex=int(_PENDING_TTL.total_seconds())
        )
        return code

    def pop_pending(self, *, code: str) -> OAuthIdentity | None:
        key = f"viewer:oauth_pending:{code}"
        raw = self._client.get(key)
        if raw is None:
            return None
        self._client.delete(key)
        data = json.loads(raw)
        return OAuthIdentity(
            provider=data["provider"],
            provider_user_id=data["provider_user_id"],
            email=data["email"],
            name=data["name"],
        )
