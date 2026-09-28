"""모바일 전용 refresh token 저장소 — auth:refresh:mobile:{userId} 네임스페이스.

웹의 RefreshTokenStore(refresh_store.py, auth:refresh:{jti} — jti 키 전역 네임스페이스)와
물리적으로 분리된 키 공간을 쓴다. 모바일 로그아웃/로테이션이 웹 세션에 영향을 주지
않고, 그 반대도 성립하도록 하기 위함(하네스 R3). 한 유저당 활성 모바일 세션은 1개로
단순화한다(동시 다중 기기 지원은 이번 범위 밖).

refresh_token 문자열 자체에 "{userId}:{secret}" 형태로 userId를 실어 보낸다 — 그래야
클라이언트가 refresh/logout 요청 시 userId를 별도로 안 보내도(RefreshRequest처럼
refresh_token 하나만으로) 어느 Redis 키를 봐야 하는지 알 수 있다.
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


class MobileTokenInvalid(Exception):
    """모바일 refresh token이 없거나 형식이 잘못되었거나 만료/불일치 — 재로그인 필요."""


@dataclass(frozen=True)
class MobileSession:
    refresh_token: str
    user_id: str
    sub: str
    aud: str
    roles: list[str]


def _key(user_id: str) -> str:
    return f"auth:refresh:mobile:{user_id}"


def _parse(refresh_token: str) -> tuple[str, str]:
    user_id, sep, secret = refresh_token.partition(":")
    if not sep or not user_id or not secret:
        raise MobileTokenInvalid("모바일 refresh_token 형식이 올바르지 않습니다.")
    return user_id, secret


class MobileRefreshTokenStore:
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def issue(self, *, user_id: str, sub: str, aud: str, roles: list[str]) -> str:
        secret = secrets.token_urlsafe(24)
        payload = json.dumps({"secret": secret, "sub": sub, "aud": aud, "roles": roles})
        self._client.set(_key(user_id), payload, ex=int(_REFRESH_TTL.total_seconds()))
        return f"{user_id}:{secret}"

    def rotate(self, *, refresh_token: str) -> MobileSession:
        """검증 후 새 refresh_token으로 교체(로테이션)한다. 저장된 값과 다르면(이미
        로테이션됐거나 위조) 해당 유저의 모바일 세션을 폐기하고 거부한다."""
        user_id, secret = _parse(refresh_token)
        raw = self._client.get(_key(user_id))
        if raw is None:
            raise MobileTokenInvalid("모바일 세션이 존재하지 않거나 만료되었습니다.")

        data = json.loads(raw)
        if data["secret"] != secret:
            self._client.delete(_key(user_id))
            raise MobileTokenInvalid(f"모바일 refresh_token 재사용 감지: user_id={user_id}")

        new_token = self.issue(
            user_id=user_id, sub=data["sub"], aud=data["aud"], roles=data["roles"]
        )
        return MobileSession(
            refresh_token=new_token,
            user_id=user_id,
            sub=data["sub"],
            aud=data["aud"],
            roles=data["roles"],
        )

    def revoke(self, *, refresh_token: str) -> None:
        """로그아웃 — 이 refresh_token이 가리키는 유저의 모바일 세션 키만 삭제한다
        (해당 유저의 웹 세션이나 다른 유저의 모바일 세션에는 영향 없음)."""
        try:
            user_id, secret = _parse(refresh_token)
        except MobileTokenInvalid:
            return
        raw = self._client.get(_key(user_id))
        if raw is None:
            return
        data = json.loads(raw)
        if data["secret"] == secret:
            self._client.delete(_key(user_id))

    def revoke_user(self, *, user_id: str) -> None:
        """회원 탈퇴 — 이 사용자의 모바일 세션을 무조건 폐기한다."""
        self._client.delete(_key(user_id))
