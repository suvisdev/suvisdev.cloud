"""사이트별 crawl-batch 마지막 실행 시각 — 레디스에 ISO 문자열로 저장한다."""

from __future__ import annotations

import os
from datetime import datetime

import redis

from ontology.app.ports.output.crawl_schedule_state_port import CrawlScheduleStatePort

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisCrawlScheduleStateAdapter(CrawlScheduleStatePort):
    def __init__(self, *, redis_url: str = _REDIS_URL) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, site_id: str) -> str:
        return f"ontology:crawl_schedule:last_run:{site_id}"

    def get_last_run(self, site_id: str) -> datetime | None:
        value = self._client.get(self._key(site_id))
        return datetime.fromisoformat(str(value)) if value else None

    def set_last_run(self, site_id: str, at: datetime) -> None:
        self._client.set(self._key(site_id), at.isoformat())
