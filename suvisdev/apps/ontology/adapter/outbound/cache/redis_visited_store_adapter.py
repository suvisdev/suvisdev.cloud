"""키워드별 방문 URL — 레디스 Set(SADD)으로 원자적 dedup. 같은 키워드 재실행 시 재수집 방지."""

from __future__ import annotations

import os

import redis

from ontology.app.ports.output.visited_store_port import VisitedStorePort

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisVisitedStoreAdapter(VisitedStorePort):
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, keyword: str) -> str:
        return f"ontology:visited:{keyword}"

    def is_visited(self, keyword: str, url: str) -> bool:
        return bool(self._client.sismember(self._key(keyword), url))

    def mark(self, keyword: str, url: str) -> None:
        self._client.sadd(self._key(keyword), url)
