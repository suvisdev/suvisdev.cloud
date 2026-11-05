from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from news.app.dtos.news_dtos import (
    ArticleDto,
    CollectReport,
    SectionDto,
    SummaryReport,
    TopicCreateCommand,
    TopicDto,
    TopicUpdateCommand,
)


class NewsCollectUseCase(ABC):
    @abstractmethod
    async def collect_once(self) -> CollectReport:
        """RSS(섹션별) + 검색어 탭을 한 번 모으고, 판정 범위 기사만 규칙 판정까지 한다."""


class NewsSummarizeUseCase(ABC):
    @abstractmethod
    async def summarize_pending(self, limit: int) -> SummaryReport:
        """요약이 없는 기사를 limit 건까지 한국어 제목·요약한다(AI 섹션 먼저)."""


class NewsReadUseCase(ABC):
    @abstractmethod
    async def list_sections(self) -> list[SectionDto]:
        """섹션(ai 메인·economy 부록)과 그 안의 출처 묶음·피드 이름."""

    @abstractmethod
    async def list_public_topics(self, section: str | None = None) -> list[TopicDto]: ...

    @abstractmethod
    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]: ...

    @abstractmethod
    async def list_latest(
        self, *, section: str, group: str | None, limit: int, before: datetime | None
    ) -> list[ArticleDto]: ...

    @abstractmethod
    async def search(
        self, query: str, *, section: str, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        """모아 둔 기사 검색 — 외부 검색 API 를 부르지 않는다(방문자 검색이 할당량을 쓰지 않게)."""


class NewsTopicAdminUseCase(ABC):
    @abstractmethod
    async def list_topics(self) -> list[TopicDto]: ...

    @abstractmethod
    async def create_topic(self, command: TopicCreateCommand) -> TopicDto: ...

    @abstractmethod
    async def update_topic(self, command: TopicUpdateCommand) -> TopicDto: ...

    @abstractmethod
    async def delete_topic(self, topic_id: int) -> None: ...
