from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from news.app.dtos.news_dtos import (
    ArticleDto,
    FetchedArticle,
    StoredArticle,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
    VerdictCommand,
)


class NewsRepositoryPort(ABC):
    # 검색어 탭
    @abstractmethod
    async def list_topics(self, *, public_only: bool, active_only: bool) -> list[TopicDto]: ...

    @abstractmethod
    async def get_topic(self, topic_id: int) -> TopicDto | None: ...

    @abstractmethod
    async def find_topic_by_query(self, query: str) -> TopicDto | None: ...

    @abstractmethod
    async def create_topic(self, command: TopicCreateCommand) -> TopicDto: ...

    @abstractmethod
    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto | None: ...

    @abstractmethod
    async def delete_topic(self, topic_id: int) -> bool: ...

    # 기사
    @abstractmethod
    async def save_articles(self, items: Sequence[FetchedArticle]) -> list[StoredArticle]:
        """canonical_url 기준으로 없으면 넣고, 있으면 그대로 둔다. 입력 순서와 상관없이 주소마다 1건."""

    @abstractmethod
    async def link_topic_articles(
        self, topic_id: int, pairs: Sequence[tuple[int, float]]
    ) -> None: ...

    @abstractmethod
    async def missing_verdicts(
        self, article_ids: Sequence[int], harness_version: str, layer: str
    ) -> set[int]:
        """해당 층(layer)의 현재 하네스 버전 판정이 없는 기사 id."""

    @abstractmethod
    async def save_verdicts(self, commands: Sequence[VerdictCommand]) -> None: ...

    @abstractmethod
    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]: ...

    @abstractmethod
    async def list_latest(self, *, limit: int, before: datetime | None) -> list[ArticleDto]: ...
