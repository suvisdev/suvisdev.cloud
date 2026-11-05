"""공개 읽기 — 검색어 탭 목록, 탭별 기사, 최신 뉴스. news.suvisdev.cloud 는 로그인 없이 이것만 쓴다."""

from __future__ import annotations

from datetime import datetime

from news.app.dtos.news_dtos import ArticleDto, TopicDto
from news.app.errors import TopicNotFoundError
from news.app.ports.input.news_use_cases import NewsReadUseCase
from news.app.ports.output.news_repository import NewsRepositoryPort

MAX_LIMIT = 100


class NewsReadInteractor(NewsReadUseCase):
    def __init__(self, repository: NewsRepositoryPort) -> None:
        self._repository = repository

    async def list_public_topics(self) -> list[TopicDto]:
        return await self._repository.list_topics(public_only=True, active_only=True)

    async def list_topic_articles(
        self, topic_id: int, *, limit: int, before: datetime | None
    ) -> list[ArticleDto]:
        topic = await self._repository.get_topic(topic_id)
        # 비공개·꺼진 탭은 없는 것과 같게 다룬다 (존재 여부를 흘리지 않는다)
        if topic is None or not topic.is_public or not topic.active:
            raise TopicNotFoundError(topic_id)
        return await self._repository.list_topic_articles(
            topic_id, limit=_clamp(limit), before=before
        )

    async def list_latest(self, *, limit: int, before: datetime | None) -> list[ArticleDto]:
        return await self._repository.list_latest(limit=_clamp(limit), before=before)


def _clamp(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))
