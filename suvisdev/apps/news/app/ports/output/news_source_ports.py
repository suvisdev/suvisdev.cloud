from __future__ import annotations

from abc import ABC, abstractmethod

from news.app.dtos.news_dtos import FeedSource, FetchedArticle


class NewsSearchPort(ABC):
    """검색어로 기사 목록을 받는다 (네이버 뉴스 검색 API)."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """키가 없으면 False — 수집기는 검색어 수집을 건너뛰고 최신 뉴스(RSS)만 모은다."""

    @abstractmethod
    async def search(self, query: str, display: int = 100) -> list[FetchedArticle]: ...


class FeedReaderPort(ABC):
    """언론사 RSS 에서 최신 기사를 받는다."""

    @abstractmethod
    async def read(self, feed: FeedSource) -> list[FetchedArticle]: ...
