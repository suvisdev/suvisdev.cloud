from __future__ import annotations

from abc import ABC, abstractmethod


class PageFetcherPort(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """URL의 raw HTML을 가져온다. 실패 시 CrawlFetchError를 던진다."""
