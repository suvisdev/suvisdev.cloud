from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from news.app.dtos.news_dtos import (
    ArticleDto,
    CollectReport,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
)


class NewsCollectUseCase(ABC):
    @abstractmethod
    async def collect_once(self) -> CollectReport:
        """검색어 탭(검색 API) + 최신 뉴스(RSS) 를 한 번 모으고 규칙 판정까지 한다."""


class NewsReadUseCase(ABC):
    @abstractmethod
    async def list_public_topics(self) -> list[TopicDto]: ...

    @abstractmethod
    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]: ...

    @abstractmethod
    async def list_latest(self, *, limit: int, before: datetime | None) -> list[ArticleDto]: ...


class NewsTopicAdminUseCase(ABC):
    @abstractmethod
    async def list_topics(self) -> list[TopicDto]: ...

    @abstractmethod
    async def create_topic(self, command: TopicCreateCommand) -> TopicDto: ...

    @abstractmethod
    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto: ...

    @abstractmethod
    async def delete_topic(self, topic_id: int) -> None: ...
