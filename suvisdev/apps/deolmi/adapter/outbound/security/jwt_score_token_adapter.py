"""점수 토큰을 HS256 JWT로 서명한다 — 위조와 재사용(리플레이) 차단.

서명 열쇠는 DEOLMI_TOKEN_SECRET(사용자 세션용 JWT_SECRET과 별개). 토큰마다 jti를 넣고,
검증에 쓴 jti는 만료까지 Redis(REDIS_URL, 키 `deolmi:jti:*`)에 SET NX로 남겨 다시 못 쓰게 한다.
서빙 기기가 노트북↔집컴으로 바뀌거나 파드가 재시작돼도 두 기기가 같은 Redis를 보므로 재사용이 막힌다.
Redis에 닿지 못하면 TokenStoreUnavailableError(503) — 재사용을 못 막는 채로 통과시키지 않는다.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

import jwt
import redis

from deolmi.app.dtos.score_dto import ScoreTokenPayload
from deolmi.app.errors import (
    TokenExpiredError,
    TokenInvalidError,
    TokenReusedError,
    TokenStoreUnavailableError,
)
from deolmi.app.ports.output.score_token_port import ScoreTokenPort

_ALG = "HS256"
TOKEN_TTL_S = 120


class JwtScoreTokenAdapter(ScoreTokenPort):
    def __init__(self, secret: str, client: redis.Redis, ttl_s: int = TOKEN_TTL_S) -> None:
        self._secret = secret
        self._client = client
        self._ttl = ttl_s

    def issue(self, site_key: str, result: dict[str, Any]) -> str:
        now = int(time.time())
        payload = {
            "jti": secrets.token_hex(8),
            "sk": site_key,
            "res": result,
            "iat": now,
            "exp": now + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALG)

    def decode(self, token: str) -> ScoreTokenPayload:
        try:
            p = jwt.decode(token, self._secret, algorithms=[_ALG])
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("token expired") from e
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError("invalid token") from e
        return ScoreTokenPayload(
            jti=str(p["jti"]), site_key=str(p["sk"]), expires_at=float(p["exp"]), result=p["res"]
        )

    def consume(self, payload: ScoreTokenPayload) -> None:
        # 토큰이 만료되면 어차피 decode에서 걸리므로 기록도 그때까지만 둔다(+1초 여유).
        ttl = max(int(payload.expires_at - time.time()) + 1, 1)
        try:
            first = self._client.set(f"deolmi:jti:{payload.jti}", "1", nx=True, ex=ttl)
        except redis.RedisError as e:
            raise TokenStoreUnavailableError("token store unavailable") from e
        if not first:
            raise TokenReusedError("token already used")
