from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from news.app.dtos.news_dtos import (
    ArticleDto,
    FetchedArticle,
    HotUpdate,
    StoredArticle,
    SummaryTarget,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
    VerdictCommand,
)
from news.domain.ko_summary import KoSummary


class NewsRepositoryPort(ABC):
    # 검색어 탭
    @abstractmethod
    async def list_topics(
        self, *, public_only: bool, active_only: bool, section: str | None = None
    ) -> list[TopicDto]: ...

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
    async def list_latest(
        self, *, section: str, group: str | None, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        """RSS 로 모은 기사(origin=feed) 최신순. group 이 있으면 그 묶음만."""

    # 오늘의 핫한 소식
    @abstractmethod
    async def set_hot(self, updates: Sequence[HotUpdate]) -> None: ...

    @abstractmethod
    async def list_hot(self, source: str, *, limit: int, since: datetime) -> list[ArticleDto]:
        """since 이후에 수치가 갱신된 글을 그 출처의 수치 높은 순으로."""

    # 한국어 제목·요약
    @abstractmethod
    async def pending_summaries(self, *, limit: int, max_tries: int) -> list[SummaryTarget]:
        """요약이 없고 실패가 max_tries 번 미만인 기사. AI 섹션 먼저, 그 안에서 최신순."""

    @abstractmethod
    async def save_summary(self, article_id: int, summary: KoSummary, model: str) -> None: ...

    @abstractmethod
    async def mark_summary_failed(self, article_id: int) -> None: ...

    @abstractmethod
    async def search_articles(
        self, tokens: Sequence[str], *, section: str, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        """모아 둔 기사에서 제목·요약에 단어가 모두 들어간 것 최신순 (대소문자 무시)."""
