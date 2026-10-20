"""점수 토큰을 HS256 JWT로 서명한다 — 위조와 재사용(리플레이) 차단.

서명 열쇠는 DEOLMI_TOKEN_SECRET(사용자 세션용 JWT_SECRET과 별개). 토큰마다 jti를 넣고,
검증에 쓴 jti는 만료까지 메모리에 기억해 다시 못 쓰게 한다. backend가 replicas 1이라
메모리로 충분하다 — 여러 파드로 늘리면 Redis로 옮겨야 한다.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

import jwt

from deolmi.app.dtos.score_dto import ScoreTokenPayload
from deolmi.app.errors import TokenExpiredError, TokenInvalidError, TokenReusedError
from deolmi.app.ports.output.score_token_port import ScoreTokenPort

_ALG = "HS256"
TOKEN_TTL_S = 120


class JwtScoreTokenAdapter(ScoreTokenPort):
    def __init__(self, secret: str, ttl_s: int = TOKEN_TTL_S) -> None:
        self._secret = secret
        self._ttl = ttl_s
        self._used: dict[str, float] = {}  # jti -> exp

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
        now = time.time()
        for jti in [k for k, exp in self._used.items() if exp < now]:
            del self._used[jti]
        if payload.jti in self._used:
            raise TokenReusedError("token already used")
        self._used[payload.jti] = payload.expires_at
