"""아침 메일 하루 한 통 기록(Redis). 발송이 MAX_TRIES 번 실패하면 그날은 멈춘다(틀린 비밀번호로 온종일 분류하지 않게).
분류 모델 장애는 세지 않는다 — 발송을 시도하지도 않았으니 모델이 돌아오면 그날 메일을 보낸다.

잠금은 분류·발송 시간(수 분)을 넉넉히 덮고 다음 수집 주기(30분) 전에 풀린다.
Redis 가 안 되면 예외가 그대로 올라간다 — 기록 없이 보내면 주기마다 중복 발송되기 때문이다.
"""

from __future__ import annotations

from datetime import date

import redis

from news.app.ports.output.news_digest_ports import DigestLedgerPort

MAX_TRIES = 3
_LOCK_S = 15 * 60
_KEEP_S = 3 * 24 * 3600


class RedisDigestLedger(DigestLedgerPort):
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def begin(self, day: date) -> bool:
        key = f"news:digest:{day.isoformat()}"
        if self._client.get(key) is not None:
            return False
        if int(self._client.get(f"{key}:failures") or 0) >= MAX_TRIES:
            return False
        return bool(self._client.set(f"{key}:lock", "1", nx=True, ex=_LOCK_S))

    def record_failure(self, day: date) -> None:
        key = f"news:digest:{day.isoformat()}:failures"
        self._client.incr(key)
        self._client.expire(key, _KEEP_S)

    def finish(self, day: date) -> None:
        self._client.set(f"news:digest:{day.isoformat()}", "sent", ex=_KEEP_S)
