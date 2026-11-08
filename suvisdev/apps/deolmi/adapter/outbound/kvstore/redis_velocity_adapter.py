"""출처별 요청 속도 — 예매 폭주·어뷰징의 1차 신호. DB를 거치지 않아 빠르다.

Redis(REDIS_URL) INCR+EXPIRE 고정 창(ontology redis_rate_limiter와 같은 방식). 서빙 기기가
노트북↔집컴으로 바뀌어도 같은 Redis를 보므로 창이 끊기지 않는다. 고정 창이라 경계에서
최대 두 배까지 덜 셀 수 있다 — 속도는 차단 근거가 아니라 의심 신호라 충분하다.
Redis가 죽으면 0을 돌려준다(fail-open): 속도 신호 하나 때문에 채점 전체를 멈추지 않는다.
"""

from __future__ import annotations

import logging
import time

import redis

from deolmi.app.ports.output.velocity_port import VelocityPort

logger = logging.getLogger(__name__)


class RedisVelocityAdapter(VelocityPort):
    def __init__(self, client: redis.Redis, window_s: int = 10) -> None:
        self._client = client
        self._window = window_s

    def record(self, key: str) -> int:
        bucket = int(time.time() // self._window)
        rkey = f"deolmi:vel:{key}:{bucket}"
        try:
            count = int(self._client.incr(rkey))
            if count == 1:
                self._client.expire(rkey, self._window + 1)
        except redis.RedisError:
            logger.warning("[deolmi] 속도 기록 실패(Redis) — 속도 신호 없이 채점한다")
            return 0
        return count
