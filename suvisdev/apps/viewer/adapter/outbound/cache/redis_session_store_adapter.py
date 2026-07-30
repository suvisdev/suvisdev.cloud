"""OAuth 로그인 세션 — JWT 발급 + Redis 저장.

프로바이더(google/naver/kakao) 신원 확인이 끝나면, 프로바이더별 토큰 형식과
무관하게 이 서버가 직접 서명한 세션 JWT 하나로 통일해 Redis에 저장한다.
세션 JWT를 리다이렉트 URL에 그대로 실어 보내지 않고(브라우저 히스토리·Referer
노출 방지) 1회용 handoff code만 담아 보낸다 — 프론트는 POST /viewer/oauth/exchange로
그 code를 실제 세션(JWT)과 맞바꾼다. handoff code도 Redis에 저장하며 1회 소비 후 삭제한다.
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta

import jwt
import redis

from viewer.app.dtos.oauth_dto import SessionPayloadDto
from viewer.app.ports.output.session_store_port import SessionStorePort

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_JWT_SECRET = os.getenv("JWT_SECRET", "")
_SESSION_TTL = timedelta(days=7)
_HANDOFF_TTL = timedelta(seconds=60)


def _resolve_role(email: str | None) -> str:
    """RBAC — ADMIN_EMAILS(콤마 구분, env)에 있는 이메일만 admin, 나머지는 user."""
    admin_emails = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    return "admin" if email and email.lower() in admin_emails else "user"


class RedisSessionStoreAdapter(SessionStorePort):
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def issue_session(
        self, *, user_id: int, username: str, nickname: str, email: str | None
    ) -> str:
        if not _JWT_SECRET:
            raise RuntimeError("JWT_SECRET이 설정되지 않았습니다.")

        role = _resolve_role(email)
        jti = secrets.token_urlsafe(16)
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "username": username,
                "role": role,
                "jti": jti,
                "iat": now,
                "exp": now + _SESSION_TTL,
            },
            _JWT_SECRET,
            algorithm="HS256",
        )
        self._client.set(f"viewer:session:{jti}", token, ex=int(_SESSION_TTL.total_seconds()))

        handoff_code = secrets.token_urlsafe(24)
        self._client.set(
            f"viewer:oauth_handoff:{handoff_code}",
            f"{user_id}\t{username}\t{nickname}\t{role}\t{token}",
            ex=int(_HANDOFF_TTL.total_seconds()),
        )
        return handoff_code

    def redeem_handoff_code(self, *, code: str) -> SessionPayloadDto | None:
        key = f"viewer:oauth_handoff:{code}"
        raw = self._client.get(key)
        if raw is None:
            return None
        self._client.delete(key)
        user_id_str, username, nickname, role, token = raw.split("\t", 4)
        return SessionPayloadDto(
            user_id=int(user_id_str), username=username, nickname=nickname, token=token, role=role
        )
