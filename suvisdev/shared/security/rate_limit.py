"""공개(무인증) LLM 엔드포인트의 IP별 요청 제한 — 최근 60초에 20회, Redis에 센다.

2026-11-13: ontology·mova에 복사본으로 있던 프로세스 메모리 카운터를 합쳤다. 메모리 카운터는 main 머지마다
CD가 backend를 다시 띄울 때 0이 됐다. Redis는 별도 컨테이너라 재시작과 무관하다.
최근 60초 슬라이딩 로그(ZSET)를 Lua로 원자 처리한다 — 고정 창이면 창 경계 2초에 두 배(40회)가 통과한다.
Redis가 응답하지 않으면 그 엔드포인트만 503으로 막는다(비용 방어가 목적이라 열어 두지 않는다).
"""

from __future__ import annotations

import logging
import os
import time
import uuid

import redis
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# 허용이면 0, 초과면 다시 시도할 수 있을 때까지 남은 초(올림, 최소 1)
_SLIDING_LOG = """
local key, now, window, limit = KEYS[1], tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
if redis.call('ZCARD', key) >= limit then
  local oldest = tonumber(redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2])
  return math.max(1, math.ceil(oldest + window - now))
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, window + 1)
return 0
"""


def client_ip(request: Request) -> str:
    # Cloudflare(cloudflared) 뒤에서는 CF-Connecting-IP가 신뢰 가능한 원 IP다(터널 외 경로 없음, 11-13 확인).
    # X-Forwarded-For의 "첫" 요소는 클라이언트가 위조할 수 있어(요청마다 난수 → 제한 우회, 2026-09-11 리뷰)
    # 가장 가까운 프록시가 기록한 마지막 요소를 쓴다.
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimit:
    """FastAPI 의존성. scope마다 따로 센다 — 홈 채팅과 mova 채팅은 각자 20회다."""

    def __init__(
        self,
        scope: str,
        *,
        max_requests: int = 20,
        window_seconds: int = 60,
        redis_url: str | None = None,
    ) -> None:
        self._scope = scope
        self._max = max_requests
        self._window = window_seconds
        client = redis.from_url(  # 연결은 첫 요청 때 맺는다
            redis_url or os.getenv("REDIS_URL") or "redis://localhost:6379/0",
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        self._script = client.register_script(_SLIDING_LOG)

    def __call__(self, request: Request) -> None:
        key = f"ratelimit:{self._scope}:{client_ip(request)}"
        try:
            retry_after = int(
                self._script(
                    keys=[key], args=[time.time(), self._window, self._max, uuid.uuid4().hex]
                )
            )
        except redis.RedisError as e:
            logger.warning("[rate-limit] Redis 응답 없음 — %s 요청을 막는다: %s", self._scope, e)
            raise HTTPException(status_code=503, detail="잠시 후 다시 시도하세요.") from None
        if retry_after:
            raise HTTPException(
                status_code=429,
                detail="요청이 너무 많습니다. 잠시 후 다시 시도하세요.",
                headers={"Retry-After": str(retry_after)},
            )
