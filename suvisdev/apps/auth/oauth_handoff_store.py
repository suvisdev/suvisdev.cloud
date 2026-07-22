"""OAuth 콜백 완료 후 프론트에 토큰을 바로 노출하지 않기 위한 1회용 handoff code.

viewer의 oauth_router.py와 같은 패턴 — 콜백은 토큰을 URL에 직접 싣지 않고
handoff code만 실어 프론트로 리다이렉트하고, 프론트가 POST /auth/exchange로
code를 실제 토큰과 맞바꾼다. 키 접두사는 "auth:"로 분리(viewer의
"viewer:oauth_handoff:*"와 겹치지 않음).
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import timedelta

import redis

from auth.schemas import TokenResponse

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_HANDOFF_TTL = timedelta(seconds=60)


class OAuthHandoffStore:
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def save(self, token_response: TokenResponse) -> str:
        code = secrets.token_urlsafe(24)
        self._client.set(
            f"auth:oauth_handoff:{code}",
            token_response.model_dump_json(),
            ex=int(_HANDOFF_TTL.total_seconds()),
        )
        return code

    def pop(self, code: str) -> TokenResponse | None:
        key = f"auth:oauth_handoff:{code}"
        raw = self._client.get(key)
        if raw is None:
            return None
        self._client.delete(key)
        return TokenResponse.model_validate_json(raw)
