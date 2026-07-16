"""도메인별 요청 간격 제한 — INCR+EXPIRE로 "interval초짜리 버킷당 1요청"을 강제한다.

여러 CLI 프로세스가 동시에 같은 도메인을 긁어도(예: 두 keyword를 병렬 실행) 레디스가
공유 상태라 전역으로 간격이 지켜진다 — 프로세스 내 메모리 카운터로는 안 되는 부분.
버킷을 이미 다른 요청이 선점했으면(INCR 결과가 1보다 큼) 다음 버킷까지 짧게 재시도한다.
"""

from __future__ import annotations

import os
import time

import redis

from ontology.app.ports.output.rate_limiter_port import RateLimiterPort

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisRateLimiterAdapter(RateLimiterPort):
    def __init__(self, *, interval_seconds: float, redis_url: str = _REDIS_URL) -> None:
        self._interval = max(interval_seconds, 0.001)
        self._client = redis.from_url(redis_url, decode_responses=True)

    def acquire(self, domain: str) -> None:
        while True:
            bucket = int(time.time() / self._interval)
            key = f"ontology:ratelimit:{domain}:{bucket}"
            count = self._client.incr(key)
            if count == 1:
                self._client.expire(key, int(self._interval) + 1)
            if count <= 1:
                return
            time.sleep(min(self._interval / 2, 0.5))
