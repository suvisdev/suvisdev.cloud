from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class CrawlScheduleStatePort(ABC):
    """사이트별 마지막 crawl-batch 실행 시각 — interval이 지났는지 판단하는 데 쓴다."""

    @abstractmethod
    def get_last_run(self, site_id: str) -> datetime | None: ...

    @abstractmethod
    def set_last_run(self, site_id: str, at: datetime) -> None: ...
